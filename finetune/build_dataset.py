"""
Build the OSLLM fine-tuning dataset (chat format, JSONL).

Every number in the dataset comes from core/scheduler_engine.py (CPU scheduling, checked by
finetune/verify_engine.py against an independent simulator and OSTEP's reference simulator) or from
core/os_solvers.py (Banker's, deadlock detection, page replacement, disk scheduling, memory allocation,
checked by finetune/verify_solvers.py against separate reference implementations).

Example types
  solve       full worked solution: decision-by-decision steps, Gantt chart, table, averages
  quick       single calculations: TAT/WT/RT of one process, throughput, utilisation,
              exponential averaging, RR waiting bound, rate-monotonic test
  mistake     a student's answer with a typical error (or no error) -> diagnosis + correction
  compare     the same processes under 2-3 algorithms -> table + why they differ
  quantum     Round Robin with several quanta -> effect of the quantum
  task        Banker's / detection / page replacement / disk / memory allocation numericals, solved step by step
  task_compare  the same input under 2-3 of those algorithms -> table + why they differ
  concept     hand-written concept answers (finetune/concept_qa.py and concept_qa_syllabus.py), several phrasings each
  mood        any of the above asked in a confused / anxious / rushed / frustrated / formal way,
              answered in the matching style
  refusal     questions outside Operating Systems -> polite refusal and suggestions

Output (finetune/data/): train.jsonl, val.jsonl, test.jsonl, eval_numericals.json, eval_tasks.json, stats.json

Run:  python finetune/build_dataset.py [--scale 1.0] [--seed 2026]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from core.scheduler_engine import ALGORITHMS, Process, solve  # noqa: E402
from concept_qa import QA as QA_CPU  # noqa: E402
from concept_qa_syllabus import QA_MORE  # noqa: E402
from core import os_solvers, problems  # noqa: E402

QA = QA_CPU + QA_MORE

OUT = Path(__file__).resolve().parent / "data"

SYSTEM = ("You are OSLLM, the tutor for the Operating Systems course (BCSE303L): OS structure, system calls, "
          "processes, threads, IPC, CPU scheduling, synchronization, deadlocks, memory management, virtual memory, "
          "file systems, disk scheduling and Linux commands. Explain step by step so the student understands. "
          "Conventions: TAT = CT - AT, WT = TAT - BT, RT = first time on CPU - AT; a lower priority number means "
          "higher priority; ties go to the earlier arrival, then the lower process number; in Round Robin a process "
          "arriving when a quantum expires joins the queue before the preempted process. Banker's algorithm uses "
          "repeated passes in process order; SCAN and C-SCAN go to the disk edge and the C-SCAN / C-LOOK return jump "
          "is counted; next fit resumes at the hole used last. If a question is not about Operating Systems, say so "
          "politely.")

ALGO_NAMES = {
    "FCFS": ["FCFS", "First Come First Served (FCFS)", "FIFO scheduling", "first-come first-served scheduling"],
    "SJF": ["SJF", "non-preemptive SJF", "Shortest Job First (non-preemptive)", "shortest job first scheduling"],
    "SRTF": ["SRTF", "preemptive SJF", "Shortest Remaining Time First (SRTF)", "shortest remaining time first"],
    "PRIORITY_NP": ["non-preemptive priority scheduling", "priority scheduling (non-preemptive)",
                    "non-preemptive priority"],
    "PRIORITY_P": ["preemptive priority scheduling", "priority scheduling (preemptive)", "preemptive priority"],
    "RR": ["Round Robin with time quantum {q}", "RR (q = {q})", "Round Robin scheduling, quantum = {q}",
           "round robin with a time slice of {q}"],
}
RULE = {
    "FCFS": "processes run in order of arrival, each to completion (non-preemptive)",
    "SJF": "when the CPU is free, pick the arrived process with the shortest burst; it runs to completion",
    "SRTF": "always run the arrived process with the shortest remaining time; a new arrival with a shorter time "
            "preempts the running process",
    "PRIORITY_NP": "when the CPU is free, pick the arrived process with the highest priority (lowest number); "
                   "it runs to completion",
    "PRIORITY_P": "always run the arrived process with the highest priority (lowest number); a higher-priority "
                  "arrival preempts the running process",
    "RR": "run the process at the front of the ready queue for at most one quantum; if it is not finished, it "
          "goes to the back of the queue",
}
ASKS = [
    ("Draw the Gantt chart and find the average waiting time and average turnaround time.", False),
    ("Find the completion, turnaround and waiting time of each process, and the averages.", False),
    ("Calculate the average TAT and average WT. Show the Gantt chart.", False),
    ("Solve it step by step.", False),
    ("Find CT, TAT, WT and response time for every process, and the averages.", True),
    ("Compute average waiting time, average turnaround time and average response time.", True),
]
LEADS = ["Solve using {algo}.", "Using {algo}, schedule these processes.", "Apply {algo} to the following processes.",
         "Consider the processes below scheduled with {algo}.", "{algo}:", "Schedule with {algo}."]


# ------------------------------------------------------------------ problems
def random_problem(rng: random.Random, algo: str, n_range=(3, 6)):
    n = rng.randint(*n_range)
    style = rng.choices(["zero", "staggered", "gaps", "ties"], [2, 5, 1.5, 1.5])[0]
    if style == "zero":
        arr = [0] * n
    elif style == "staggered":
        arr = sorted(rng.randint(0, 2 * n) for _ in range(n))
        arr[0] = 0 if rng.random() < 0.8 else arr[0]
    elif style == "gaps":
        arr = sorted(rng.choice([0, 1, 2, 3, 12, 14, 20]) for _ in range(n))
    else:
        arr = sorted(rng.choice([0, 0, 2, 2, 4]) for _ in range(n))
    bursts = [rng.randint(1, 10) for _ in range(n)]
    pri = [rng.randint(1, 5) for _ in range(n)] if algo.startswith("PRIORITY") else [0] * n
    q = rng.randint(1, 5) if algo == "RR" else None
    procs = [Process(f"P{i + 1}", arr[i], bursts[i], pri[i]) for i in range(n)]
    return procs, q


def fmt_num(x: float) -> str:
    return str(int(round(x))) if abs(x - round(x)) < 1e-9 else f"{x:.2f}"


def render_processes(rng, procs, algo, q):
    pr = algo.startswith("PRIORITY")
    unit = rng.choice(["", "", " ms"])
    style = rng.choice(["inline", "table", "lists", "sentences"])
    if style == "inline":
        parts = [f"{p.pid} (AT {p.arrival}, BT {p.burst}" + (f", priority {p.priority}" if pr else "") + ")"
                 for p in procs]
        text = "Processes: " + ", ".join(parts) + "."
    elif style == "table":
        head = "| Process | Arrival time | Burst time |" + (" Priority |" if pr else "")
        sep = "|---|---|---|" + ("---|" if pr else "")
        rows = [f"| {p.pid} | {p.arrival} | {p.burst} |" + (f" {p.priority} |" if pr else "") for p in procs]
        text = "\n".join([head, sep, *rows])
    elif style == "lists":
        text = (f"Processes {', '.join(p.pid for p in procs)}. Arrival times: "
                f"{', '.join(str(p.arrival) for p in procs)}. Burst times{unit and ' (ms)'}: "
                f"{', '.join(str(p.burst) for p in procs)}.")
        if pr:
            text += f" Priorities: {', '.join(str(p.priority) for p in procs)}."
    else:
        text = " ".join(f"{p.pid} arrives at {p.arrival}{unit} and needs {p.burst}{unit}"
                        + (f" with priority {p.priority}" if pr else "") + "." for p in procs)
    if pr and rng.random() < 0.6:
        text += " A lower number means higher priority."
    return text


def question(rng, procs, algo, q):
    name = rng.choice(ALGO_NAMES[algo]).format(q=q)
    ask, want_rt = rng.choice(ASKS)
    lead = rng.choice(LEADS).format(algo=name)
    body = render_processes(rng, procs, algo, q)
    return f"{lead}\n{body}\n{ask}" if "\n" in body else f"{lead} {body} {ask}", want_rt


# ------------------------------------------------------------------ answer pieces
def gantt_text(res) -> str:
    labels = [("idle" if s.pid == "IDLE" else s.pid) for s in res.gantt]
    widths = [max(len(lbl) + 2, len(str(s.end)) + 2, 4) for lbl, s in zip(labels, res.gantt)]
    top = "|" + "|".join(lbl.center(w) for lbl, w in zip(labels, widths)) + "|"
    times = [" "] * (len(top) + 4)
    pos = 0
    marks = [(0, res.gantt[0].start)]
    for w, s in zip(widths, res.gantt):
        pos += w + 1
        marks.append((pos, s.end))
    for p, t in marks:
        for k, ch in enumerate(str(t)):
            if p + k < len(times):
                times[p + k] = ch
    return "```\n" + top + "\n" + "".join(times).rstrip() + "\n```"


def steps_text(res) -> str:
    out = []
    for s in res.steps:
        runs = "CPU idle" if s["runs"] == "IDLE" else f"**{s['runs']}** runs"
        out.append(f"- t = {s['time']}: ready queue [{s['ready']}] → {runs}. {s['why']}")
    return "\n".join(out)


def results_table(res, with_rt: bool) -> str:
    head = "| Process | AT | BT | CT | TAT = CT − AT | WT = TAT − BT |" + (" RT |" if with_rt else "")
    sep = "|---|---|---|---|---|---|" + ("---|" if with_rt else "")
    rows = []
    for pid, r in res.table.items():
        row = (f"| {pid} | {r['arrival']} | {r['burst']} | {r['completion']} | "
               f"{r['completion']} − {r['arrival']} = {r['turnaround']} | "
               f"{r['turnaround']} − {r['burst']} = {r['waiting']} |")
        if with_rt:
            row += f" {r['response']} |"
        rows.append(row)
    return "\n".join([head, sep, *rows])


def averages_text(res, with_rt: bool) -> str:
    n = len(res.table)
    tats = [r["turnaround"] for r in res.table.values()]
    wts = [r["waiting"] for r in res.table.values()]
    lines = [f"Average TAT = ({' + '.join(map(str, tats))}) / {n} = {sum(tats)} / {n} = **{fmt_num(res.avg_tat)}**",
             f"Average WT = ({' + '.join(map(str, wts))}) / {n} = {sum(wts)} / {n} = **{fmt_num(res.avg_wt)}**"]
    if with_rt:
        rts = [r["response"] for r in res.table.values()]
        lines.append(f"Average RT = ({' + '.join(map(str, rts))}) / {n} = {sum(rts)} / {n} = "
                     f"**{fmt_num(res.avg_rt)}**")
    return "\n\n".join(lines)


def full_solution(res, algo, with_rt: bool) -> str:
    q = f" (time quantum {res.time_quantum})" if algo == "RR" else ""
    return (f"**{ALGORITHMS[algo]}{q}**: {RULE[algo]}.\n\n**Step by step**\n{steps_text(res)}\n\n"
            f"**Gantt chart**\n{gantt_text(res)}\n\n**Results**\n{results_table(res, with_rt)}\n\n"
            f"{averages_text(res, with_rt)}")


def compact_solution(res, algo) -> str:
    return (f"**Gantt chart**\n{gantt_text(res)}\n\nAverage TAT = **{fmt_num(res.avg_tat)}**, "
            f"Average WT = **{fmt_num(res.avg_wt)}**, Average RT = **{fmt_num(res.avg_rt)}**")


def chat(user: str, assistant: str, kind: str, meta: dict | None = None) -> dict:
    return {"messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user},
                         {"role": "assistant", "content": assistant}], "kind": kind, "meta": meta or {}}


TEST_PROBLEMS: set[str] = set()          # process sets used in the test split (any algorithm)


def procs_key(procs) -> str:
    return ";".join(f"{p.arrival},{p.burst},{p.priority}" for p in procs)


def fresh_problem(rng, algo, n_range=(3, 6)):
    """A random problem whose process set is not in the test split."""
    while True:
        procs, q = random_problem(rng, algo, n_range)
        if procs_key(procs) not in TEST_PROBLEMS:
            return procs, q


def signature(procs, algo, q) -> str:
    return f"{algo}|{q}|" + ";".join(f"{p.arrival},{p.burst},{p.priority}" for p in procs)


# ------------------------------------------------------------------ generators
def gen_solve(rng, seen, algo):
    while True:
        procs, q = random_problem(rng, algo)
        sig = signature(procs, algo, q)
        if sig not in seen and procs_key(procs) not in TEST_PROBLEMS:
            seen.add(sig)
            break
    res = solve(procs, algo, q)
    user, want_rt = question(rng, procs, algo, q)
    meta = {"algorithm": algo, "avg_tat": round(res.avg_tat, 2), "avg_wt": round(res.avg_wt, 2),
            "avg_rt": round(res.avg_rt, 2), "sig": sig}
    return chat(user, full_solution(res, algo, want_rt), "solve", meta), (procs, q, res)


def gen_quick(rng):
    kind = rng.choice(["one", "one", "preempted", "throughput", "expavg", "rrbound", "rms"])
    if kind == "one":
        at, bt = rng.randint(0, 15), rng.randint(1, 12)
        ct = at + bt + rng.randint(0, 20)
        pid = f"P{rng.randint(1, 6)}"
        u = f"{pid} arrives at time {at}, needs {bt} units of CPU and completes at time {ct}. Find its turnaround " \
            f"time and waiting time."
        tat, wt = ct - at, ct - at - bt
        a = (f"Turnaround time: TAT = CT − AT = {ct} − {at} = **{tat}**\n\nWaiting time: WT = TAT − BT = {tat} − {bt} "
             f"= **{wt}**\n\n{pid} spent {tat} units in the system, {bt} of them running, so it waited {wt}.")
        if at > 0 and rng.random() < 0.5:
            a += f"\n\nCareful: TAT is not {ct}. That would forget that {pid} only arrived at {at}."
        return chat(u, a, "quick")
    if kind == "preempted":
        at, b1, gap, b2 = rng.randint(0, 5), rng.randint(1, 5), rng.randint(1, 8), rng.randint(1, 5)
        start1 = at + rng.randint(0, 4)
        end1 = start1 + b1
        start2 = end1 + gap
        end2 = start2 + b2
        bt = b1 + b2
        u = (f"In a preemptive schedule, P2 arrives at {at} and has a burst of {bt}. It runs from {start1} to {end1} "
             f"and again from {start2} to {end2}. Find its CT, TAT, WT and RT.")
        tat = end2 - at
        a = (f"- CT = end of its last run = **{end2}**\n- TAT = CT − AT = {end2} − {at} = **{tat}**\n"
             f"- WT = TAT − BT = {tat} − {bt} = **{tat - bt}**\n- RT = first start − AT = {start1} − {at} = "
             f"**{start1 - at}**\n\nCheck: P2 waited {start1 - at} before its first run and {gap} between its runs, "
             f"{start1 - at} + {gap} = {tat - bt}, which matches WT. Using first start − AT as the waiting time would "
             f"give only the response time.")
        return chat(u, a, "quick")
    if kind == "throughput":
        n, span, idle = rng.randint(3, 8), rng.randint(15, 60), rng.randint(0, 6)
        busy = span - idle
        u = (f"A schedule of {n} processes runs from time 0 to {span}, and the CPU is idle for {idle} units in "
             f"total. Find the throughput and CPU utilisation.")
        a = (f"- Throughput = processes ÷ total time = {n} ÷ {span} = **{n / span:.3f}** processes per unit time\n"
             f"- CPU utilisation = busy time ÷ total time = ({span} − {idle}) ÷ {span} = {busy} ÷ {span} = "
             f"**{busy / span * 100:.1f}%**")
        return chat(u, a, "quick")
    if kind == "expavg":
        alpha = rng.choice([0.5, 0.5, 0.25, 0.75, 0.4, 0.6])
        tau, t = rng.randint(4, 16), rng.randint(2, 16)
        nxt = alpha * t + (1 - alpha) * tau
        u = (f"Predict the next CPU burst using exponential averaging with α = {alpha}, previous prediction "
             f"τn = {tau} and actual last burst tn = {t}.")
        a = (f"τ(n+1) = α · t(n) + (1 − α) · τ(n)\n\n= {alpha} × {t} + {1 - alpha:g} × {tau}\n\n"
             f"= {alpha * t:g} + {(1 - alpha) * tau:g} = **{nxt:g}**\n\nThe prediction moves from {tau} towards "
             f"the actual burst {t}; α decides how fast.")
        return chat(u, a, "quick")
    if kind == "rrbound":
        n, q = rng.randint(3, 10), rng.choice([5, 10, 20, 25, 50, 100])
        u = (f"In Round Robin with {n} processes in the ready queue and a time quantum of {q} ms, what is the "
             f"longest a process waits before its next turn?")
        a = (f"At most (n − 1) × q = ({n} − 1) × {q} = **{(n - 1) * q} ms**.\n\nEvery other process can run at most "
             f"one quantum before this process gets the CPU again, ignoring context-switch time.")
        return chat(u, a, "quick")
    # rate monotonic
    k = rng.randint(2, 3)
    tasks = []
    for _ in range(k):
        p = rng.choice([20, 25, 40, 50, 60, 80, 100])
        tasks.append((rng.randint(5, max(6, p // 2)), p))
    util = sum(t / p for t, p in tasks)
    bound = k * (2 ** (1 / k) - 1)
    desc = ", ".join(f"T{i + 1} (t = {t}, p = {p})" for i, (t, p) in enumerate(tasks))
    u = f"Can these periodic tasks be scheduled with rate-monotonic scheduling? {desc}"
    terms = " + ".join(f"{t}/{p}" for t, p in tasks)
    a = (f"Total utilisation U = {terms} = **{util:.3f}**\n\nRate-monotonic bound for N = {k}: N(2^(1/N) − 1) = "
         f"{k}(2^(1/{k}) − 1) = **{bound:.3f}**\n\n")
    if util <= bound:
        a += "U is within the bound, so rate-monotonic scheduling is **guaranteed** to meet all deadlines."
    elif util <= 1:
        a += ("U is above the bound but not above 1, so the bound test **cannot guarantee** it. The tasks may still "
              "be schedulable (check the timeline), and EDF can schedule them because U ≤ 1.")
    else:
        a += "U is greater than 1, so **no** algorithm can meet all deadlines on one CPU."
    return chat(u, a, "quick")


MISTAKES = ["tat_no_at", "wt_ct_minus_bt", "wt_as_rt", "correct"]


def gen_mistake(rng, seen):
    algo = rng.choice(list(ALGORITHMS))
    for _ in range(50):
        procs, q = fresh_problem(rng, algo)
        res = solve(procs, algo, q)
        kind = rng.choices(MISTAKES, [3, 3, 2, 1.2])[0]
        rows = {pid: dict(r) for pid, r in res.table.items()}
        bad = []
        for pid, r in rows.items():
            if kind == "tat_no_at" and r["arrival"] > 0:
                r["s_tat"], r["s_wt"] = r["completion"], r["completion"] - r["burst"]
                bad.append(pid)
            elif kind == "wt_ct_minus_bt" and r["arrival"] > 0:
                r["s_tat"], r["s_wt"] = r["turnaround"], r["completion"] - r["burst"]
                bad.append(pid)
            elif kind == "wt_as_rt" and r["response"] != r["waiting"]:
                r["s_tat"], r["s_wt"] = r["turnaround"], r["response"]
                bad.append(pid)
            r.setdefault("s_tat", r["turnaround"])
            r.setdefault("s_wt", r["waiting"])
        if kind == "correct" or bad:
            break
    else:
        return None
    name = rng.choice(ALGO_NAMES[algo]).format(q=q)
    body = render_processes(rng, procs, algo, q)
    student = "\n".join(["| Process | CT | TAT | WT |", "|---|---|---|---|",
                         *[f"| {pid} | {r['completion']} | {r['s_tat']} | {r['s_wt']} |" for pid, r in rows.items()]])
    n = len(rows)
    s_avg_tat = sum(r["s_tat"] for r in rows.values()) / n
    s_avg_wt = sum(r["s_wt"] for r in rows.values()) / n
    student += f"\n\nAverage TAT = {fmt_num(s_avg_tat)}, Average WT = {fmt_num(s_avg_wt)}"
    lead = rng.choice(["Check my answer.", "Is my solution correct?", "Where did I go wrong?",
                       "Please verify my working.", "I got this answer, is it right?"])
    user = f"{lead} {name}.{chr(10) if chr(10) in body else ' '}{body}\n\nMy answer:\n{student}"
    if kind == "correct":
        ans = (f"Your answer is **correct**. Every completion time matches the Gantt chart, and you used TAT = CT − AT "
               f"and WT = TAT − BT correctly.\n\n{gantt_text(res)}\n\nAverage TAT = **{fmt_num(res.avg_tat)}**, "
               f"Average WT = **{fmt_num(res.avg_wt)}**.")
    else:
        where = ", ".join(bad)
        why = {
            "tat_no_at": (f"Your completion times are right, but for {where} you used TAT = CT. Turnaround time "
                          f"starts when the process **arrives**, so it must be TAT = CT − AT. That error then "
                          f"carried into WT."),
            "wt_ct_minus_bt": (f"Your CT and TAT are right, but for {where} you wrote WT = CT − BT. That forgets the "
                               f"arrival time. Use WT = TAT − BT (which is CT − AT − BT)."),
            "wt_as_rt": (f"Your CT and TAT are right, but for {where} the waiting time you wrote is the **response "
                         f"time** (first start − arrival). In a preemptive schedule a process can wait several "
                         f"times, so use WT = TAT − BT, which adds up every wait."),
        }[kind]
        ans = (f"Not quite. {why}\n\n**Corrected results**\n{results_table(res, False)}\n\n"
               f"{averages_text(res, False)}")
    return chat(user, ans, "mistake", {"algorithm": algo, "mistake": kind})


def gen_compare(rng):
    sets = [["FCFS", "SJF"], ["SJF", "SRTF"], ["FCFS", "SJF", "SRTF"], ["FCFS", "RR"], ["SJF", "RR"],
            ["PRIORITY_NP", "PRIORITY_P"], ["FCFS", "SJF", "RR"], ["SRTF", "RR"]]
    algos = rng.choice(sets)
    has_pr = any(a.startswith("PRIORITY") for a in algos)
    procs, _ = fresh_problem(rng, "PRIORITY_NP" if has_pr else "FCFS", (4, 5))
    q = rng.randint(2, 4)
    results = {a: solve(procs, a, q if a == "RR" else None) for a in algos}
    label = {a: (f"RR (q = {q})" if a == "RR" else {"PRIORITY_NP": "Priority (non-preemptive)",
                                                      "PRIORITY_P": "Priority (preemptive)"}.get(a, a)) for a in algos}
    body = render_processes(rng, procs, "PRIORITY_NP" if has_pr else "FCFS", None)
    user = rng.choice(["Compare {x} for these processes.", "Which is better here, {x}? Show the numbers.",
                       "Solve with {x} and compare the averages."]).format(
        x=" and ".join(label[a] for a in algos)) + "\n" + body

    def switches(r):
        p = [s.pid for s in r.gantt if s.pid != "IDLE"]
        return sum(1 for x, y in zip(p, p[1:]) if x != y)

    table = ["| Algorithm | Gantt order | Avg TAT | Avg WT | Avg RT | Context switches |", "|---|---|---|---|---|---|"]
    for a in algos:
        r = results[a]
        order = " → ".join(s.pid if s.pid != "IDLE" else "idle" for s in r.gantt)
        table.append(f"| {label[a]} | {order} | {fmt_num(r.avg_tat)} | {fmt_num(r.avg_wt)} | {fmt_num(r.avg_rt)} | "
                     f"{switches(r)} |")
    best_wt = min(results[a].avg_wt for a in algos)
    winners = [label[a] for a in algos if abs(results[a].avg_wt - best_wt) < 1e-9]
    best_rt = min(results[a].avg_rt for a in algos)
    rt_win = [label[a] for a in algos if abs(results[a].avg_rt - best_rt) < 1e-9]
    notes = []
    if len(winners) == len(algos):
        notes.append("All of them give the same average waiting time here, because they end up making the same "
                     "useful choices for this particular set of processes.")
    else:
        notes.append(f"Lowest average waiting time: **{' and '.join(winners)}** ({fmt_num(best_wt)}).")
    notes.append(f"Lowest average response time: **{' and '.join(rt_win)}** ({fmt_num(best_rt)}).")
    why = {"FCFS": "FCFS ignores burst length, so a long early job makes later short jobs wait.",
           "SJF": "SJF picks the shortest arrived job whenever the CPU becomes free, which lowers waiting time, but "
                  "cannot react to a short job that arrives while another is running.",
           "SRTF": "SRTF can also preempt the running job when a shorter one arrives, so short jobs wait less, at "
                   "the cost of extra context switches.",
           "RR": f"RR gives every process a turn of at most {q}, so processes start sooner (better response time), "
                 f"but finishing is spread out and there are more context switches.",
           "PRIORITY_NP": "Non-preemptive priority picks by priority only when the CPU is free.",
           "PRIORITY_P": "Preemptive priority lets a higher-priority arrival take the CPU immediately, which helps "
                         "important processes but can make low-priority ones wait much longer."}
    ans = ("\n".join(table) + "\n\n" + "\n\n".join(notes) + "\n\n**Why they differ**\n"
           + "\n".join(f"- {why[a]}" for a in algos))
    return chat(user, ans, "compare", {"algorithms": algos})


def gen_quantum(rng):
    procs, _ = fresh_problem(rng, "RR", (3, 5))
    maxb = max(p.burst for p in procs)
    qs = sorted({1, 2, rng.choice([3, 4]), maxb})
    rows, res_by_q, sw_by_q = [], {}, {}
    for q in qs:
        r = solve(procs, "RR", q)
        res_by_q[q] = r
        p = [s.pid for s in r.gantt if s.pid != "IDLE"]
        sw = sum(1 for x, y in zip(p, p[1:]) if x != y)
        sw_by_q[q] = sw
        rows.append(f"| {q} | {fmt_num(r.avg_tat)} | {fmt_num(r.avg_wt)} | {fmt_num(r.avg_rt)} | {sw} |")
    fc = solve(procs, "FCFS")
    body = render_processes(rng, procs, "RR", None)
    user = (rng.choice(["How does the time quantum affect Round Robin for these processes?",
                        "Run Round Robin with different quanta and compare.",
                        f"Compare RR with q = {', '.join(map(str, qs))}."]) + "\n" + body)
    best = min(qs, key=lambda q: (res_by_q[q].avg_wt, q))
    best_rt = min(qs, key=lambda q: (res_by_q[q].avg_rt, q))
    most_sw = max(qs, key=lambda q: (sw_by_q[q], -q))
    ans = ("| Quantum | Avg TAT | Avg WT | Avg RT | Context switches |\n|---|---|---|---|---|\n" + "\n".join(rows)
           + f"\n\n- Lowest average response time: q = {best_rt} ({fmt_num(res_by_q[best_rt].avg_rt)}). "
             f"Most context switches: q = {most_sw} ({sw_by_q[most_sw]}). Smaller quanta let processes start "
             f"sooner but switch more often.\n"
             f"- Lowest average waiting time: q = {best} ({fmt_num(res_by_q[best].avg_wt)}).")
    big = res_by_q[maxb]
    if abs(big.avg_wt - fc.avg_wt) < 1e-9 and [s.pid for s in big.gantt] == [s.pid for s in fc.gantt]:
        ans += (f"\n- With q = {maxb}, the longest burst, every process finishes in its first turn, so RR gives "
                f"exactly the FCFS result (average WT {fmt_num(fc.avg_wt)}).")
    ans += "\n\nRule of thumb: choose q so that about 80% of CPU bursts finish within one quantum."
    return chat(user, ans, "quantum")


def gen_concepts(rng, entries):
    out = []
    for topic, qs, a in entries:
        for q in qs:
            out.append(chat(q, a, "concept", {"topic": topic}))
    return out


MOODS = {
    "confused": (["bro i dont get this at all. {q}", "i'm really confused. {q}", "can u explain simply? {q}",
                  "{q} i don't understand it"],
                 ["No problem, let's go slowly, one step at a time.\n\n"]),
    "anxious": (["My exam is tomorrow and I'm stressed. {q}", "{q} I have my viva in the morning, please help.",
                 "last minute revision, exam today: {q}"],
                ["You've got this. Here is the method step by step, which is exactly what examiners look for.\n\n"]),
    "frustrated": (["ugh, I keep getting this wrong. {q}", "this makes no sense, tried 3 times. {q}"],
                   ["That's frustrating, so let's do it a different way, one decision at a time.\n\n"]),
    "formal": (["Could you kindly explain the following? {q}", "I would like a detailed solution. {q}"],
               ["Certainly.\n\n"]),
    "rushed": (["quick: {q}", "{q} just the answer pls, short", "in short: {q}"], [""]),
}
EXAM_TIPS = ("\n\n**Quick revision**\n1. TAT = CT − AT, WT = TAT − BT.\n2. Only pick processes that have already "
             "arrived.\n3. In preemptive algorithms, re-check at every arrival.")


def gen_mood(rng, base: dict, compact: str | None):
    mood = rng.choice(list(MOODS))
    q_tpl, openers = MOODS[mood]
    q = base["messages"][1]["content"]
    if mood == "confused" or mood == "rushed":
        q = q[0].lower() + q[1:]
    user = rng.choice(q_tpl).format(q=q)
    ans = base["messages"][2]["content"]
    if mood == "rushed":
        if compact:
            ans = compact
        else:
            ans = ans.split("\n\n")[0]
    else:
        ans = rng.choice(openers) + ans
        if mood == "anxious" and base["kind"] in ("solve", "mistake"):
            ans += EXAM_TIPS
    return chat(user, ans, "mood", {"mood": mood, "base": base["kind"]})


OFF_TOPIC = [
    ("What is the difference between TCP and UDP?", None),
    ("Explain the OSI model.", None),
    ("What is normalization in DBMS?", None),
    ("Explain polymorphism in Java.", None),
    ("What is a binary search tree?", None),
    ("Write a Python program to reverse a linked list.", None),
    ("What is the capital of France?", None),
    ("Explain backpropagation in neural networks.", None),
    ("Who won the cricket world cup?", None),
    ("Write an essay on climate change.", None),
    ("Explain SQL joins.", None),
    ("What is the derivative of x squared?", None),
    ("Tell me a joke.", None),
    ("How do I install Ubuntu?", None),
]
SUGGEST = ["Give me an example of a Gantt chart and how to solve it.", "Compare SJF and SRTF.",
           "Give me a Banker's algorithm example and solve it.", "Compare FIFO, LRU and Optimal page replacement.",
           "Explain the four conditions for deadlock.", "Solve SSTF disk scheduling for a request queue.",
           "Explain Peterson's solution.", "Compare first fit, best fit and worst fit."]


def gen_refusals(rng, items):
    out = []
    for q, os_topic in items:
        for _ in range(2):
            s = rng.sample(SUGGEST, 2)
            a = (f"That's outside what I teach. I'm OSLLM, the tutor for the **Operating Systems** course: OS "
                 f"structure and system calls, processes and threads, CPU scheduling, synchronization, deadlocks, "
                 f"memory and virtual memory, file systems, disk scheduling and Linux commands. Try asking:\n"
                 f"- {s[0]}\n- {s[1]}")
            user = q if rng.random() < 0.6 else rng.choice(["hey, ", "quick question: ", "", "can you help? "]) + q
            out.append(chat(user, a, "refusal"))
    return out


# ------------------------------------------------------------------ the other numericals (os_solvers)
TASK_ASKS = {
    "BANKERS": ["Is the system in a safe state? If yes, find a safe sequence.", "Apply the Banker's algorithm and find "
                "the Need matrix and a safe sequence.", "Check whether this state is safe using the Banker's algorithm."],
    "REQUEST": ["Can the request be granted immediately? Use the Banker's algorithm.", "Should the OS grant this "
                "request? Show the resource-request algorithm."],
    "DETECT": ["Is the system deadlocked? If so, which processes are deadlocked?", "Apply the deadlock detection "
               "algorithm."],
    "page": ["Find the number of page faults using {name}.", "How many page faults occur with {name}? Show the frames "
             "after every reference.", "Using {name}, find the page faults and the hit ratio."],
    "disk": ["Find the total head movement using {name}.", "Using {name}, give the order in which requests are served "
             "and the total head movement.", "Calculate the total seek distance for {name}."],
    "alloc": ["Allocate the processes using {name}.", "Where does each process go with {name}? Which processes have to "
              "wait?", "Show the allocation using {name} and the holes left."],
}
TASK_RULE = {
    "FIFO": "replace the page that has been in memory the longest",
    "LRU": "replace the page whose last use is furthest in the past",
    "OPT": "replace the page whose next use is furthest in the future (pages never used again go first)",
    "D_FCFS": "serve requests in the order they arrived",
    "SSTF": "always move to the closest pending request",
    "SCAN": "move in the current direction serving requests up to the disk edge, then reverse",
    "C-SCAN": "move in one direction to the disk edge, jump to the other end and continue in the same direction "
              "(the jump counts)",
    "LOOK": "like SCAN, but reverse at the last request instead of the disk edge",
    "C-LOOK": "like C-SCAN, but jump from the last request to the farthest request on the other side (the jump counts)",
    "FIRST": "take the first hole that is large enough",
    "BEST": "take the smallest hole that is large enough",
    "WORST": "take the largest hole",
    "NEXT": "like first fit, but start searching at the hole used last",
    "BANKERS": "Need = Max - Allocation; start with Work = Available and repeatedly finish a process with Need <= Work",
    "REQUEST": "check Request <= Need, then Request <= Available, then pretend to grant it and run the safety check",
    "DETECT": "like the safety check, but compare each process's Request (not Need) with Work",
}
TASK_ALGOS = [a for algos in os_solvers.KIND_ALGOS.values() for a in algos]


def task_question(rng, sv) -> str:
    key = sv.algorithm if sv.kind == "bankers" else sv.kind
    ask = rng.choice(TASK_ASKS[key]).format(name=os_solvers.SHORT.get(sv.algorithm, sv.name))
    return f"{sv.problem_text()}\n\n{ask}" if rng.random() < 0.5 else f"{ask}\n\n{sv.problem_text()}"


def task_answer(sv) -> str:
    summary = "\n".join(f"- **{k}**: {v}" for k, v in sv.summary.items())
    steps = "\n".join(f"{i}. {st['text']}" for i, st in enumerate(sv.steps, 1))
    return f"**{sv.name}**: {TASK_RULE[sv.algorithm]}.\n\n**Step by step**\n{steps}\n\n**Answer**\n{summary}"


def fresh_task(rng, seen, algo):
    kind = os_solvers.kind_of(algo)
    for _ in range(50):
        inp = problems.design(kind, algo, seen, rng)
        if problems.key(inp) not in seen and problems.key(inp) not in TEST_TASKS:
            seen.add(problems.key(inp))
            return inp
    return inp


def gen_task(rng, seen, algo):
    sv = problems.solve(algo, fresh_task(rng, seen, algo))
    return chat(task_question(rng, sv), task_answer(sv), "task", {"algorithm": algo}), sv


TASK_COMPARE = {"page": ["FIFO", "LRU", "OPT"], "disk": ["D_FCFS", "SSTF", "SCAN", "C-SCAN", "LOOK", "C-LOOK"],
                "alloc": ["FIRST", "BEST", "WORST", "NEXT"]}


def gen_task_compare(rng, seen):
    kind = rng.choice(list(TASK_COMPARE))
    algos = rng.sample(TASK_COMPARE[kind], rng.choice([2, 3]))
    inp = fresh_task(rng, seen, algos[0])
    svs = [problems.solve(a, inp) for a in algos]
    names = [os_solvers.SHORT.get(a, a) for a in algos]
    q = f"Compare {', '.join(names[:-1])} and {names[-1]} for this input.\n\n{svs[0].problem_text()}"
    if kind == "page":
        rows = [f"| {n} | {sv.view['faults']} | {sv.view['hits']} |" for n, sv in zip(names, svs)]
        table = "| Algorithm | Page faults | Hits |\n|---|---|---|\n" + "\n".join(rows)
        best = min(zip(names, svs), key=lambda x: x[1].view["faults"])[0]
        why = (f"{best} has the fewest faults here. OPT is the lower bound because it looks ahead; LRU usually comes "
               "close because recently used pages tend to be used again; FIFO ignores how pages are used, so it can "
               "throw out a busy page.")
    elif kind == "disk":
        rows = [f"| {n} | {' -> '.join(map(str, sv.view['order']))} | {sv.view['total']} |" for n, sv in zip(names, svs)]
        table = "| Algorithm | Service order | Total head movement |\n|---|---|---|\n" + "\n".join(rows)
        best = min(zip(names, svs), key=lambda x: x[1].view["total"])[0]
        why = (f"{best} moves the head least here. SSTF is greedy and short on movement but can starve far requests; "
               "SCAN-type algorithms sweep, which keeps waiting times predictable; going to the disk edge or counting "
               "the return jump adds movement.")
    else:
        rows = [f"| {n} | " + ", ".join(f"{p} -> {sv.view['placed'][p] or 'waits'}" for p in sv.inputs["names"])
                + f" | {', '.join(sv.view['waiting']) or 'none'} |" for n, sv in zip(names, svs)]
        table = "| Strategy | Placement | Must wait |\n|---|---|---|\n" + "\n".join(rows)
        why = ("Best fit keeps large holes intact by using the tightest hole; worst fit splits the largest hole "
               "first, so a big process arriving later may not fit; first and next fit are fast but depend on hole "
               "order.")
    parts = [f"**{n}**\n" + "\n".join(f"{i}. {st['text']}" for i, st in enumerate(sv.steps, 1))
             for n, sv in zip(names, svs)]
    a = f"{table}\n\n" + "\n\n".join(parts) + f"\n\n**Why they differ**\n{why}"
    return chat(q, a, "task_compare", {"kind": kind})


TEST_TASKS: set[str] = set()


# ------------------------------------------------------------------ build
def build(scale: float, seed: int):
    rng = random.Random(seed)
    seen: set[str] = set()
    n = lambda x: max(1, int(x * scale))  # noqa: E731

    # held-out test numericals first, so their problems can never appear in training
    test_rng = random.Random(seed + 1)
    test, eval_items, eval_tasks = [], [], []
    for algo in ALGORITHMS:
        for _ in range(n(30)):
            ex, (procs, q, res) = gen_solve(test_rng, seen, algo)
            TEST_PROBLEMS.add(procs_key(procs))
            test.append(ex)
            eval_items.append({"question": ex["messages"][1]["content"], "algorithm": algo,
                               "avg_tat": round(res.avg_tat, 2), "avg_wt": round(res.avg_wt, 2)})
    for algo in TASK_ALGOS:
        for _ in range(n(8)):
            ex, sv = gen_task(test_rng, seen, algo)
            TEST_TASKS.add(problems.key(sv.inputs))
            test.append(ex)
            expect = ({"faults": sv.view["faults"]} if sv.kind == "page" else {"total": sv.view["total"]}
                      if sv.kind == "disk" else {"safe": sv.view["safe"]} if algo == "BANKERS" else None)
            if expect:
                eval_tasks.append({"question": ex["messages"][1]["content"], "algorithm": algo, **expect})
    test_concepts = [e for i, e in enumerate(QA) if i % 12 == 5]
    train_concepts = [e for e in QA if e not in test_concepts]
    test += gen_concepts(rng, test_concepts)
    test += gen_refusals(random.Random(seed + 2), OFF_TOPIC[::5])

    def make(split_scale: float, r: random.Random):
        k = lambda x: max(1, int(x * scale * split_scale))  # noqa: E731
        rows, compact_by_id = [], {}
        for algo in ALGORITHMS:
            for _ in range(k(500)):
                ex, (procs, q, res) = gen_solve(r, seen, algo)
                rows.append(ex)
                compact_by_id[id(ex)] = compact_solution(res, algo)
        rows += [gen_quick(r) for _ in range(k(500))]
        rows += [m for m in (gen_mistake(r, seen) for _ in range(k(650))) if m]
        rows += [gen_compare(r) for _ in range(k(450))]
        rows += [gen_quantum(r) for _ in range(k(180))]
        for algo in TASK_ALGOS:
            rows += [gen_task(r, seen, algo)[0] for _ in range(k(120))]
        rows += [gen_task_compare(r, seen) for _ in range(k(300))]
        return rows, compact_by_id

    train, compact = make(1.0, rng)
    val, _ = make(0.05, random.Random(seed + 3))
    concepts = gen_concepts(rng, train_concepts)
    train += concepts * 3                                   # concepts are rarer, so repeat them
    train += gen_refusals(rng, [x for i, x in enumerate(OFF_TOPIC) if i % 5])
    mood_pool = [e for e in train if e["kind"] in ("solve", "concept", "mistake", "quick", "task")]
    train += [gen_mood(rng, b, compact.get(id(b))) for b in rng.sample(mood_pool, n(700))]
    val += gen_concepts(random.Random(seed + 4), train_concepts[::9])
    rng.shuffle(train)
    rng.shuffle(val)

    OUT.mkdir(parents=True, exist_ok=True)
    for name, rows in (("train", train), ("val", val), ("test", test)):
        with open(OUT / f"{name}.jsonl", "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps({"messages": row["messages"], "kind": row["kind"]}, ensure_ascii=False) + "\n")
    (OUT / "eval_numericals.json").write_text(json.dumps(eval_items, indent=1), encoding="utf-8")
    (OUT / "eval_tasks.json").write_text(json.dumps(eval_tasks, indent=1), encoding="utf-8")

    def words(rows):
        return sum(len(r["messages"][2]["content"].split()) for r in rows)
    stats = {s: {"examples": len(rows), "by_kind": dict(Counter(r["kind"] for r in rows)),
                 "answer_words": words(rows)} for s, rows in (("train", train), ("val", val), ("test", test))}
    stats["unique_numerical_problems"] = len(seen)
    test_q = {r["messages"][1]["content"] for r in test}
    stats["test_questions_also_in_train"] = sum(r["messages"][1]["content"] in test_q for r in train + val)
    (OUT / "stats.json").write_text(json.dumps(stats, indent=1), encoding="utf-8")
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=float, default=1.0, help="multiply the number of generated examples")
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()
    stats = build(args.scale, args.seed)
    for split in ("train", "val", "test"):
        s = stats[split]
        kinds = ", ".join(f"{k} {v}" for k, v in sorted(s["by_kind"].items(), key=lambda x: -x[1]))
        print(f"{split:5s} {s['examples']:5d} examples  ({kinds})")
    print(f"unique numerical problems: {stats['unique_numerical_problems']}")
    print(f"test questions also in train/val: {stats['test_questions_also_in_train']}")
    print(f"written to {OUT.relative_to(ROOT)}/ (full counts in stats.json)")


if __name__ == "__main__":
    main()

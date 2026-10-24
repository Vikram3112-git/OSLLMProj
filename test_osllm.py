"""
Test OSLLM on every unit of the Operating Systems course.

  bash run.sh test                  # all tests
  bash run.sh test --quick          # one test per topic (faster)
  bash run.sh test --topic SJF      # only one topic
  bash run.sh test --list           # show the topics

Theory answers are checked for the key concepts they must mention.
Numerical answers are checked against the exact answers from the solvers
(CPU scheduling averages, page faults, total head movement, Banker's safety),
all equal to the standard textbook examples.
A full report with every answer is saved in the results/ folder.
"""
import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import config
from core.llm import LLM
from core.prompts import TUTOR_SYSTEM
from core.topic_guard import check_topic
from core import emotion


def check_ready(model):
    ok, msg = LLM(model).health()
    if not ok:
        sys.exit(msg)


def ask(question, model):
    return LLM(model).chat(TUTOR_SYSTEM, question, temperature=0.2)

# ----------------------------------------------------------------- theory tests
# (topic, question, groups of keywords) - the answer passes if it contains at
# least one keyword from EVERY group.
THEORY = [
    ("Scheduling Fundamentals",
     "What is the difference between preemptive and non-preemptive CPU scheduling?",
     [["preempt"], ["interrupt", "taken away", "take away", "forcibly", "removed", "take the cpu"],
      ["terminat", "complet", "finish", "block", "voluntar", "until"]]),
    ("Scheduling Fundamentals",
     "What does the dispatcher do, and what is dispatch latency?",
     [["context switch"], ["user mode"], ["latency"]]),
    ("Scheduling Fundamentals",
     "Explain the long-term, short-term and medium-term schedulers.",
     [["long-term", "long term"], ["short-term", "short term"], ["medium-term", "medium term"],
      ["swap"], ["multiprogramming"]]),
    ("Scheduling Criteria",
     "List the CPU scheduling criteria and say which should be maximised and which minimised.",
     [["utili"], ["throughput"], ["turnaround"], ["waiting"], ["response"], ["maxim"], ["minim"]]),
    ("Scheduling Criteria",
     "Give the formulas for turnaround time, waiting time and response time.",
     [["completion"], ["arrival"], ["burst"], ["first"]]),
    ("FCFS",
     "What is the convoy effect in FCFS scheduling?",
     [["long", "cpu-bound", "cpu bound"], ["short", "i/o-bound", "i/o bound"], ["wait"]]),
    ("SJF",
     "Why is SJF scheduling called optimal, and what is its main practical difficulty?",
     [["minimum", "lowest", "minimi", "smallest"], ["average waiting"],
      ["predict", "estimat", "unknown", "not known"]]),
    ("SJF",
     "How is the length of the next CPU burst predicted for SJF scheduling?",
     [["exponential"], ["average"], ["alpha", "α"]]),
    ("SRTF",
     "How does SRTF differ from non-preemptive SJF?",
     [["preempt"], ["remaining"], ["arriv"]]),
    ("Priority",
     "What is starvation in priority scheduling and how is it solved?",
     [["starvation", "indefinite"], ["aging", "ageing"], ["low"]]),
    ("Round Robin",
     "How does the size of the time quantum affect Round Robin scheduling?",
     [["fcfs", "first-come", "first come"], ["context switch"], ["overhead"]]),
    ("Multilevel Queues",
     "Differentiate between multilevel queue and multilevel feedback queue scheduling.",
     [["permanent", "fixed"], ["move", "between queues"], ["aging", "ageing", "starvation"]]),
    ("Multiprocessor & Real-Time",
     "What is processor affinity, and how does load balancing work in multiprocessor scheduling?",
     [["cache"], ["soft"], ["hard"], ["push", "pull", "migrat"]]),
    ("Multiprocessor & Real-Time",
     "Compare rate-monotonic scheduling and earliest deadline first scheduling.",
     [["period"], ["deadline"], ["static", "fixed"], ["dynamic"]]),
    ("Multiprocessor & Real-Time",
     "How does the Linux Completely Fair Scheduler (CFS) choose the next task to run?",
     [["virtual runtime", "vruntime"], ["red-black", "red black"]]),
    ("System Calls & Interrupts",
     "What happens, step by step, when a user program makes a system call?",
     [["trap", "interrupt", "syscall instruction"], ["kernel mode"], ["user mode"], ["table", "number"]]),
    ("Processes & Process Operations",
     "How many processes exist after a program calls fork() three times in a row? Explain.",
     [["8", "eight"], ["2^", "2³", "doubl", "power"]]),
    ("Threads & Multithreading",
     "What do threads of the same process share, and what does each thread have of its own?",
     [["code", "text"], ["data", "heap", "global"], ["stack"], ["register", "program counter"]]),
    ("Critical Section & Peterson's Solution",
     "What three requirements must a solution to the critical-section problem satisfy?",
     [["mutual exclusion"], ["progress"], ["bounded waiting"]]),
    ("Mutex Locks & Semaphores",
     "Explain the wait and signal operations of a semaphore.",
     [["wait", "p("], ["signal", "v("], ["atomic", "indivisib"], ["decrement", "s--", "- 1", "−"]]),
    ("Classical Synchronization Problems",
     "Solve the bounded-buffer producer-consumer problem using semaphores.",
     [["mutex"], ["empty"], ["full"]]),
    ("Deadlock Characterization",
     "What are the four necessary conditions for a deadlock?",
     [["mutual exclusion"], ["hold and wait"], ["no preemption"], ["circular wait"]]),
    ("Deadlock Prevention & Avoidance (Banker's)",
     "Does an unsafe state always mean the system is deadlocked?",
     [["no", "not necessarily", "does not"], ["safe sequence", "safe state"]]),
    ("Paging & Segmentation",
     "With a page size of 1 KB, page 3 maps to frame 9. Translate logical address 3085 to a physical address.",
     [["9229"], ["offset"], ["13"]]),
    ("Page Replacement",
     "What is Belady's anomaly, and which page replacement algorithm suffers from it?",
     [["fifo"], ["more frames", "increas"], ["more page faults", "more faults", "increase in"]]),
    ("Thrashing & Working Set",
     "What is thrashing and how does the working-set model prevent it?",
     [["paging", "page faults"], ["working set"], ["window", "Δ", "delta"], ["suspend", "swap out", "reduce"]]),
    ("File Systems",
     "Compare contiguous, linked and indexed file allocation.",
     [["contiguous"], ["linked", "pointer"], ["index"], ["external fragmentation"]]),
    ("Linux Commands",
     "What permissions does chmod 754 give?",
     [["rwx"], ["r-x"], ["r--"], ["owner", "user"]]),
]

# ------------------------------------------------------------ topic scope tests
# (question, should OSLLM answer it?)  OSLLM must stay on Operating Systems.
SCOPE = [
    ("What is the capital of France?", False),
    ("Write a Python program to sort a list.", False),
    ("What is normalization in DBMS?", False),
    ("Explain the four necessary conditions for deadlock.", True),
    ("How does the CPU decide which job runs next?", True),
    ("What does chmod 754 do?", True),
]

# ------------------------------------------------------------ mood and tone tests
# (message, expected mood, expected tone or None). Checked without the LLM.
MOOD = [
    ("bro i dont get round robin at all pls help", "confused", "casual"),
    ("ugh this is wrong again, so annoying!!", "frustrated", None),
    ("My CAT exam is tomorrow and I'm stressed about scheduling", "anxious", None),
    ("quick: formula for waiting time", "rushed", None),
    ("thanks!! that makes sense now", "happy", None),
    ("Could you please elaborate on multilevel feedback queues?", "neutral", "formal"),
    ("why does Linux use CFS instead of plain round robin? curious", "curious", None),
]

# -------------------------------------------------------------- numerical tests
# (topic, algorithm name, processes (pid, AT, BT, priority), quantum, avg TAT, avg WT)
NUMERICAL = [
    ("FCFS", "FCFS", [("P1", 0, 24, 0), ("P2", 0, 3, 0), ("P3", 0, 3, 0)], None, 27.00, 17.00),
    ("FCFS", "FCFS", [("P1", 0, 5, 0), ("P2", 1, 3, 0), ("P3", 2, 8, 0), ("P4", 3, 6, 0)], None, 11.25, 5.75),
    ("SJF", "non-preemptive SJF", [("P1", 0, 6, 0), ("P2", 0, 8, 0), ("P3", 0, 7, 0), ("P4", 0, 3, 0)], None, 13.00, 7.00),
    ("SJF", "non-preemptive SJF", [("P1", 0, 7, 0), ("P2", 2, 4, 0), ("P3", 4, 1, 0), ("P4", 5, 4, 0)], None, 8.00, 4.00),
    ("SRTF", "SRTF (preemptive SJF)", [("P1", 0, 8, 0), ("P2", 1, 4, 0), ("P3", 2, 9, 0), ("P4", 3, 5, 0)], None, 13.00, 6.50),
    ("SRTF", "SRTF (preemptive SJF)", [("P1", 0, 7, 0), ("P2", 2, 4, 0), ("P3", 4, 1, 0), ("P4", 5, 4, 0)], None, 7.00, 3.00),
    ("Priority", "non-preemptive Priority scheduling",
     [("P1", 0, 10, 3), ("P2", 0, 1, 1), ("P3", 0, 2, 4), ("P4", 0, 1, 5), ("P5", 0, 5, 2)], None, 12.00, 8.20),
    ("Priority", "non-preemptive Priority scheduling",
     [("P1", 0, 4, 3), ("P2", 1, 3, 1), ("P3", 2, 2, 4), ("P4", 3, 5, 2)], None, 7.75, 4.25),
    ("Priority", "preemptive Priority scheduling",
     [("P1", 0, 4, 3), ("P2", 1, 3, 1), ("P3", 2, 2, 4), ("P4", 3, 5, 2)], None, 8.25, 4.75),
    ("Priority", "preemptive Priority scheduling",
     [("P1", 0, 5, 2), ("P2", 2, 3, 1), ("P3", 3, 4, 3), ("P4", 6, 2, 1)], None, 6.50, 3.00),
    ("Round Robin", "Round Robin", [("P1", 0, 24, 0), ("P2", 0, 3, 0), ("P3", 0, 3, 0)], 4, 15.67, 5.67),
    ("Round Robin", "Round Robin", [("P1", 0, 5, 0), ("P2", 1, 4, 0), ("P3", 2, 2, 0), ("P4", 4, 1, 0)], 2, 7.75, 4.75),
]

# ------------------------------------------- numericals outside CPU scheduling
# (topic, question, what to report on the FINAL line, expected value) - textbook examples, checked with core/os_solvers.py
TASKS = [
    ("Page Replacement", "Reference string 7 0 1 2 0 3 0 4 2 3 0 3 2 1 2 0 1 7 0 1 with 3 frames. How many page faults "
     "occur with FIFO page replacement?", "page faults", 15),
    ("Page Replacement", "Reference string 7 0 1 2 0 3 0 4 2 3 0 3 2 1 2 0 1 7 0 1 with 3 frames. How many page faults "
     "occur with LRU page replacement?", "page faults", 12),
    ("Page Replacement", "Reference string 7 0 1 2 0 3 0 4 2 3 0 3 2 1 2 0 1 7 0 1 with 3 frames. How many page faults "
     "occur with Optimal page replacement?", "page faults", 9),
    ("Disk Scheduling", "Disk requests 98, 183, 37, 122, 14, 124, 65, 67; the head is at 53; cylinders 0 to 199. Find "
     "the total head movement with SSTF.", "total head movement", 236),
    ("Disk Scheduling", "Disk requests 98, 183, 37, 122, 14, 124, 65, 67; the head is at 53; cylinders 0 to 199. Find "
     "the total head movement with FCFS.", "total head movement", 640),
    ("Deadlock Prevention & Avoidance (Banker's)", "Five processes P0-P4 and resources A, B, C. Available (3, 3, 2). "
     "Allocation: P0 (0,1,0), P1 (2,0,0), P2 (3,0,2), P3 (2,1,1), P4 (0,0,2). Max: P0 (7,5,3), P1 (3,2,2), "
     "P2 (9,0,2), P3 (2,2,2), P4 (4,3,3). Is the system in a safe state? Use the Banker's algorithm.", "safe", "safe"),
]
TASK_FINAL = "\nEnd with one last line in exactly this format:\nFINAL: {what} = <answer>"

FINAL_INSTRUCTION = ("\nAfter your solution, end with one last line in exactly this format:\n"
                     "FINAL: Average TAT = <number>, Average WT = <number>")
TOLERANCE = 0.051   # accepts answers rounded to 1 or 2 decimals


def numerical_question(algo, procs, quantum):
    has_priority = "Priority" in algo
    parts = []
    for pid, at, bt, pr in procs:
        parts.append(f"{pid} (AT {at}, BT {bt}" + (f", Priority {pr})" if has_priority else ")"))
    q = f"Solve using {algo}" + (f" with time quantum {quantum}" if quantum else "") + ". "
    q += "Processes: " + ", ".join(parts) + ". "
    if has_priority:
        q += "A lower priority number means higher priority. "
    q += "Draw the Gantt chart and find CT, TAT and WT for each process, and the average TAT and average WT."
    return q + FINAL_INSTRUCTION


def extract_averages(answer):
    m = re.search(r"FINAL:.*?TAT\s*[=:]\s*([\d.]+).*?WT\s*[=:]\s*([\d.]+)", answer, re.I | re.S)
    if m:
        return float(m.group(1).rstrip(".")), float(m.group(2).rstrip("."))
    tat = re.findall(r"average\s+(?:turnaround\s+time|tat)[^0-9\n]*?([\d.]+)", answer, re.I)
    wt = re.findall(r"average\s+(?:waiting\s+time|wt)[^0-9\n]*?([\d.]+)", answer, re.I)
    try:
        return (float(tat[-1].rstrip(".")) if tat else None,
                float(wt[-1].rstrip(".")) if wt else None)
    except ValueError:
        return None, None


def build_tests(args):
    tests = [{"topic": t, "kind": "theory", "question": q, "groups": g} for t, q, g in THEORY]
    tests += [{"topic": "Stays on topic", "kind": "scope", "question": q, "expect": e} for q, e in SCOPE]
    tests += [{"topic": "Senses mood and tone", "kind": "mood", "question": q, "mood": m, "tone": tn}
              for q, m, tn in MOOD]
    for topic, q, what, expect in TASKS:
        tests.append({"topic": topic, "kind": "task", "question": q + TASK_FINAL.format(what=what),
                      "what": what, "expect": expect})
    for topic, algo, procs, quantum, tat, wt in NUMERICAL:
        tests.append({"topic": topic, "kind": "numerical", "question": numerical_question(algo, procs, quantum),
                      "label": f"{algo}" + (f", q={quantum}" if quantum else "") + f", {len(procs)} processes",
                      "tat": tat, "wt": wt})
    if args.topic:
        tests = [t for t in tests if args.topic.lower() in t["topic"].lower()]
    if args.quick:
        seen, quick = set(), []
        for t in tests:
            key = (t["topic"], t["kind"])
            if key not in seen:
                seen.add(key)
                quick.append(t)
        tests = quick
    return tests


def grade(test, answer):
    if test["kind"] == "mood":
        got = json.loads(answer)
        ok = got["mood"] == test["mood"] and (test["tone"] is None or got["tone"] == test["tone"])
        return ok, f"expected {test['mood']}" + (f"/{test['tone']}" if test["tone"] else "") + \
            f" | got {got['mood']}/{got['tone']}"
    if test["kind"] == "scope":
        answered = answer != "OFF-TOPIC"
        ok = answered == test["expect"]
        return ok, f"{'answered' if answered else 'refused'} (should {'answer' if test['expect'] else 'refuse'})"
    if test["kind"] == "task":
        m = re.findall(r"FINAL:\s*" + test["what"] + r"\s*[=:]\s*\**\s*([A-Za-z]+|\d+)", answer, re.I)
        got = m[-1].lower() if m else None
        ok = got == str(test["expect"]).lower()
        return ok, f"expected {test['what']} = {test['expect']} | got {got}"
    if test["kind"] == "theory":
        text = answer.lower()
        missing = [g[0] for g in test["groups"] if not any(k in text for k in g)]
        return not missing, ("all key concepts present" if not missing
                             else "missing: " + ", ".join(missing))
    tat, wt = extract_averages(answer)
    ok = (tat is not None and wt is not None
          and abs(tat - test["tat"]) <= TOLERANCE and abs(wt - test["wt"]) <= TOLERANCE)
    return ok, f"expected TAT {test['tat']:.2f}, WT {test['wt']:.2f} | got TAT {tat}, WT {wt}"


def main():
    p = argparse.ArgumentParser(description="Test OSLLM on every unit of the Operating Systems course")
    p.add_argument("--topic", help="test only topics containing this text, e.g. SJF")
    p.add_argument("--quick", action="store_true", help="one theory + one numerical test per topic")
    p.add_argument("--list", action="store_true", help="list topics and exit")
    p.add_argument("--model", default=config.LLM_MODEL)
    args = p.parse_args()

    tests = build_tests(args)
    if args.list:
        topics = {}
        for t in build_tests(argparse.Namespace(topic=None, quick=False)):
            topics.setdefault(t["topic"], []).append(t["kind"])
        for name, kinds in topics.items():
            parts = [f"{kinds.count(k)} {k}" for k in ("theory", "numerical", "task", "scope", "mood") if kinds.count(k)]
            print(f"  {name:42s} {', '.join(parts)}")
        return
    if not tests:
        sys.exit("No tests match that topic. Use --list to see topics.")

    check_ready(args.model)
    print(f"Testing {args.model} on {len(tests)} questions. This can take a while on CPU.\n")
    results, log = [], []
    start = time.time()
    for i, t in enumerate(tests, 1):
        title = t["label"] if t["kind"] == "numerical" else t["question"]
        print(f"[{i}/{len(tests)}] {t['topic']} ({t['kind']}): {title[:70]}", flush=True)
        t0 = time.time()
        try:
            if t["kind"] == "mood":
                r = emotion.read(t["question"])
                answer = json.dumps({"mood": r.mood, "tone": r.tone})
            elif t["kind"] == "scope":
                on_topic, _ = check_topic(t["question"], LLM(args.model))
                answer = "ON-TOPIC" if on_topic else "OFF-TOPIC"
            else:
                answer = ask(t["question"], args.model)
            ok, detail = grade(t, answer)
        except Exception as e:
            answer, ok, detail = "", False, f"error: {e}"
        results.append((t, ok))
        print(f"      {'PASS' if ok else 'FAIL'}  {detail}  ({time.time() - t0:.0f}s)\n", flush=True)
        log.append(f"### [{'PASS' if ok else 'FAIL'}] {t['topic']} ({t['kind']})\nQ: {t['question']}\n"
                   f"Check: {detail}\n\n{answer}\n\n{'-' * 70}\n")

    # summary
    by_topic = {}
    for t, ok in results:
        s = by_topic.setdefault(t["topic"], [0, 0])
        s[0] += ok
        s[1] += 1
    passed = sum(ok for _, ok in results)
    lines = ["=" * 60, " OSLLM TEST REPORT", "=" * 60,
             f" {'Topic':28s} {'Passed':>8s}   Score"]
    for topic, (p_, n) in by_topic.items():
        lines.append(f" {topic:28s} {p_:>3d} / {n:<3d}  {p_ / n:6.0%}")
    lines += ["-" * 60,
              f" {'OVERALL':28s} {passed:>3d} / {len(results):<3d}  {passed / len(results):6.0%}",
              f" Time taken: {(time.time() - start) / 60:.1f} min", "=" * 60]
    summary = "\n".join(lines)
    print(summary)

    out_dir = Path(__file__).resolve().parent / "results"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"report_{datetime.now():%Y%m%d_%H%M%S}.txt"
    out.write_text(summary + "\n\n" + "\n".join(log), encoding="utf-8")
    print(f"\nFull answers saved to: {out}")


if __name__ == "__main__":
    main()

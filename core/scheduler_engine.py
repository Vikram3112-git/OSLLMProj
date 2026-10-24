"""
Deterministic CPU-scheduling engine.

Gives the exact Gantt chart, CT, TAT, WT, RT and a step-by-step decision trace
(what was in the ready queue at each decision and why a process was chosen).
The LLM uses this as ground truth so its explanations never contain wrong numbers.

Conventions:
  * TAT = CT - AT,  WT = TAT - BT,  RT = first CPU start - AT
  * Lower priority number = higher priority
  * Ties broken by earlier arrival, then by lower process index (P1 before P2)
  * Round Robin: a process arriving at the same instant a quantum expires
    joins the ready queue BEFORE the preempted process.
  * Time starts at the earliest arrival.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

ALGORITHMS = {
    "FCFS": "First-Come, First-Served (non-preemptive)",
    "SJF": "Shortest Job First (non-preemptive)",
    "SRTF": "Shortest Remaining Time First (preemptive SJF)",
    "PRIORITY_NP": "Priority Scheduling (non-preemptive)",
    "PRIORITY_P": "Priority Scheduling (preemptive)",
    "RR": "Round Robin",
}


@dataclass
class Process:
    pid: str
    arrival: int
    burst: int
    priority: int = 0


@dataclass
class Slice:
    pid: str  # "IDLE" when the CPU is idle
    start: int
    end: int


@dataclass
class ScheduleResult:
    algorithm: str
    gantt: list[Slice]
    table: dict[str, dict]
    avg_tat: float
    avg_wt: float
    avg_rt: float
    throughput: float
    cpu_utilization: float
    time_quantum: int | None = None
    order: list[str] = field(default_factory=list)
    steps: list[dict] = field(default_factory=list)

    def gantt_text(self) -> str:
        return " | ".join(f"{s.pid} [{s.start}-{s.end}]" for s in self.gantt)

    def table_text(self) -> str:
        lines = ["PID | AT | BT | PR | CT | TAT | WT | RT"]
        for pid, r in self.table.items():
            lines.append(
                f"{pid} | {r['arrival']} | {r['burst']} | {r['priority']} | "
                f"{r['completion']} | {r['turnaround']} | {r['waiting']} | {r['response']}"
            )
        lines.append(
            f"Average TAT = {self.avg_tat:.2f}, Average WT = {self.avg_wt:.2f}, "
            f"Average RT = {self.avg_rt:.2f}"
        )
        return "\n".join(lines)

    def steps_text(self) -> str:
        return "\n".join(f"t={s['time']}: ready [{s['ready']}] -> {s['runs']}. {s['why']}" for s in self.steps)


def _merge(gantt: list[Slice]) -> list[Slice]:
    merged: list[Slice] = []
    for s in gantt:
        if merged and merged[-1].pid == s.pid and merged[-1].end == s.start:
            merged[-1] = Slice(s.pid, merged[-1].start, s.end)
        else:
            merged.append(Slice(s.pid, s.start, s.end))
    return merged


# rule description used in the trace: (phrase, label, value function)
_RULES = {
    "FCFS": ("arrived first", "AT", lambda p, rem: p.arrival),
    "SJF": ("has the shortest burst time", "BT", lambda p, rem: p.burst),
    "PRIORITY_NP": ("has the highest priority", "Pr", lambda p, rem: p.priority),
    "SRTF": ("has the shortest remaining time", "rem", lambda p, rem: rem[p.pid]),
    "PRIORITY_P": ("has the highest priority", "Pr", lambda p, rem: p.priority),
}


def _non_preemptive(procs: list[Process], algo: str):
    phrase, label, val = _RULES[algo]
    idx = {p.pid: i for i, p in enumerate(procs)}
    t = min(p.arrival for p in procs)
    done: set[str] = set()
    gantt, steps = [], []
    while len(done) < len(procs):
        ready = [p for p in procs if p.arrival <= t and p.pid not in done]
        if not ready:
            nxt = min(p.arrival for p in procs if p.pid not in done)
            gantt.append(Slice("IDLE", t, nxt))
            steps.append({"time": t, "ready": "empty", "runs": "IDLE",
                          "why": f"No process has arrived yet, so the CPU stays idle until t={nxt}."})
            t = nxt
            continue
        ready.sort(key=lambda p: (val(p, None), p.arrival, idx[p.pid]))
        p = ready[0]
        if len(ready) == 1:
            why = f"{p.pid} is the only process in the ready queue"
        else:
            why = f"{p.pid} {phrase} ({label}={val(p, None)})"
            if val(ready[1], None) == val(p, None):
                why += ", tie broken by earlier arrival / lower process number"
        why += f". Non-preemptive, so it runs to completion: {t} to {t + p.burst}."
        steps.append({"time": t, "ready": ", ".join(f"{q.pid}({label}={val(q, None)})" for q in ready),
                      "runs": p.pid, "why": why})
        gantt.append(Slice(p.pid, t, t + p.burst))
        t += p.burst
        done.add(p.pid)
    return gantt, steps


def _preemptive(procs: list[Process], algo: str):
    phrase, label, val = _RULES[algo]
    idx = {p.pid: i for i, p in enumerate(procs)}
    rem = {p.pid: p.burst for p in procs}
    t = min(p.arrival for p in procs)
    gantt, steps = [], []
    prev = None
    finished_now: list[str] = []
    while any(r > 0 for r in rem.values()):
        ready = [p for p in procs if p.arrival <= t and rem[p.pid] > 0]
        if not ready:
            nxt = min(p.arrival for p in procs if rem[p.pid] > 0)
            gantt.append(Slice("IDLE", t, nxt))
            steps.append({"time": t, "ready": "empty", "runs": "IDLE",
                          "why": f"No process is ready, so the CPU stays idle until t={nxt}."})
            t, prev = nxt, None
            continue
        ready.sort(key=lambda p: (val(p, rem), p.arrival, idx[p.pid]))
        p = ready[0]
        arrived = [q.pid for q in procs if q.arrival == t and t > min(x.arrival for x in procs)]
        if p.pid != prev or arrived:
            done_txt = f"{', '.join(finished_now)} finished. " if finished_now else ""
            arr_txt = f"{', '.join(arrived)} arrived. " if arrived else ""
            if prev is not None and p.pid != prev and rem.get(prev, 0) > 0:
                prev_p = next(q for q in procs if q.pid == prev)
                why = (f"{p.pid} ({label}={val(p, rem)}) preempts {prev} "
                       f"({label}={val(prev_p, rem)}) because it {phrase}.")
            elif p.pid == prev:
                why = f"{p.pid} still {phrase} ({label}={val(p, rem)}), so it keeps running."
            elif len(ready) == 1:
                why = f"{p.pid} is the only process ready."
            else:
                why = f"{p.pid} {phrase} ({label}={val(p, rem)})"
                if val(ready[1], rem) == val(p, rem):
                    why += ", tie broken by earlier arrival / lower process number"
                why += "."
            steps.append({"time": t, "ready": ", ".join(f"{q.pid}({label}={val(q, rem)})" for q in ready),
                          "runs": p.pid, "why": done_txt + arr_txt + why})
        gantt.append(Slice(p.pid, t, t + 1))
        rem[p.pid] -= 1
        t += 1
        finished_now = [p.pid] if rem[p.pid] == 0 else []
        prev = p.pid
    return gantt, steps


def _round_robin(procs: list[Process], quantum: int):
    idx = {p.pid: i for i, p in enumerate(procs)}
    order = sorted(procs, key=lambda p: (p.arrival, idx[p.pid]))
    rem = {p.pid: p.burst for p in procs}
    queue: deque[Process] = deque()
    gantt, steps = [], []
    i = 0
    t = order[0].arrival

    def admit(upto: int) -> list[str]:
        nonlocal i
        new = []
        while i < len(order) and order[i].arrival <= upto:
            queue.append(order[i])
            new.append(order[i].pid)
            i += 1
        return new

    admit(t)
    while queue or i < len(order):
        if not queue:
            nxt = order[i].arrival
            gantt.append(Slice("IDLE", t, nxt))
            steps.append({"time": t, "ready": "empty", "runs": "IDLE",
                          "why": f"The ready queue is empty, so the CPU stays idle until t={nxt}."})
            t = nxt
            admit(t)
            continue
        snapshot = ", ".join(f"{q.pid}(rem={rem[q.pid]})" for q in queue)
        p = queue.popleft()
        run = min(quantum, rem[p.pid])
        gantt.append(Slice(p.pid, t, t + run))
        t += run
        rem[p.pid] -= run
        new = admit(t)
        if rem[p.pid] == 0:
            why = f"{p.pid} is at the front of the queue and runs {run} unit(s), finishing at t={t}."
        else:
            why = (f"{p.pid} is at the front of the queue and runs for one quantum ({run}). "
                   f"It still needs {rem[p.pid]}, so it goes to the back of the queue")
            why += f" (after {', '.join(new)}, who arrived by t={t})." if new else "."
            queue.append(p)
        if new and rem[p.pid] == 0:
            why += f" Meanwhile {', '.join(new)} joined the queue."
        steps.append({"time": t - run, "ready": snapshot, "runs": p.pid, "why": why})
    return gantt, steps


def solve(processes: list[Process], algorithm: str, time_quantum: int | None = None) -> ScheduleResult:
    if algorithm not in ALGORITHMS:
        raise ValueError(f"Unknown algorithm {algorithm}")
    if not processes:
        raise ValueError("No processes given")
    procs = list(processes)

    if algorithm in ("FCFS", "SJF", "PRIORITY_NP"):
        raw, steps = _non_preemptive(procs, algorithm)
    elif algorithm in ("SRTF", "PRIORITY_P"):
        raw, steps = _preemptive(procs, algorithm)
    else:
        if not time_quantum or time_quantum < 1:
            raise ValueError("Round Robin needs a positive time quantum")
        raw, steps = _round_robin(procs, time_quantum)

    gantt = _merge(raw)
    first_start: dict[str, int] = {}
    completion: dict[str, int] = {}
    for s in gantt:
        if s.pid == "IDLE":
            continue
        first_start.setdefault(s.pid, s.start)
        completion[s.pid] = s.end

    table: dict[str, dict] = {}
    for p in procs:
        ct = completion[p.pid]
        tat = ct - p.arrival
        table[p.pid] = {
            "arrival": p.arrival, "burst": p.burst, "priority": p.priority,
            "completion": ct, "turnaround": tat, "waiting": tat - p.burst,
            "response": first_start[p.pid] - p.arrival,
        }

    n = len(procs)
    span = gantt[-1].end - gantt[0].start
    busy = sum(s.end - s.start for s in gantt if s.pid != "IDLE")
    return ScheduleResult(
        algorithm=algorithm, gantt=gantt, table=table,
        avg_tat=sum(r["turnaround"] for r in table.values()) / n,
        avg_wt=sum(r["waiting"] for r in table.values()) / n,
        avg_rt=sum(r["response"] for r in table.values()) / n,
        throughput=n / span if span else 0.0,
        cpu_utilization=busy / span if span else 0.0,
        time_quantum=time_quantum if algorithm == "RR" else None,
        order=[s.pid for s in gantt],
        steps=steps,
    )


def processes_from_dicts(items: list[dict]) -> list[Process]:
    return [
        Process(pid=str(d["pid"]).strip().upper(), arrival=int(d["arrival"]),
                burst=int(d["burst"]), priority=int(d.get("priority", 0) or 0))
        for d in items
    ]

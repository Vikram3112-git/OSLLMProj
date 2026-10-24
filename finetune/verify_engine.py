"""
Check that the scheduling engine is correct before we generate training data from it.

1. An independent, tick-by-tick simulator (written separately, no shared code) must give
   the same CT / TAT / WT / RT as the engine for random problems with arrivals, idle gaps,
   ties, preemption and priorities, for all six algorithms.
2. Invariants must hold for every schedule: busy time + idle time = schedule length,
   WT >= 0, RT <= WT, and RT == WT for non-preemptive algorithms.
3. Optionally, if the OSTEP homework simulator (scheduler.py) is present, FCFS / SJF / RR
   results must match it (it only supports jobs that all arrive at time 0).

Run:  python finetune/verify_engine.py [--n 5000] [--ostep path/to/scheduler.py]
"""
from __future__ import annotations

import argparse
import random
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.scheduler_engine import Process, solve  # noqa: E402

ALGOS = ["FCFS", "SJF", "SRTF", "PRIORITY_NP", "PRIORITY_P", "RR"]


def tick_sim(procs: list[tuple], algo: str, q: int | None):
    """Independent reference: advance time one unit at a time.
    procs = [(pid, arrival, burst, priority)] in process-number order."""
    n = len(procs)
    rem = [b for _, _, b, _ in procs]
    first = [None] * n
    done = [None] * n
    t = min(a for _, a, _, _ in procs)
    queue: list[int] = []          # RR ready queue (indices)
    seen = [False] * n
    running, slice_left = None, 0
    while any(d is None for d in done):
        # arrivals at time t join the RR queue in process-number order
        for i in range(n):
            if not seen[i] and procs[i][1] <= t:
                seen[i] = True
                queue.append(i)
        if algo == "RR":
            if running is not None and (rem[running] == 0 or slice_left == 0):
                if rem[running] > 0:
                    queue.append(running)          # after the processes that arrived by now
                running = None
            if running is None and queue:
                running = queue.pop(0)
                slice_left = q
        else:
            ready = [i for i in range(n) if seen[i] and rem[i] > 0]
            key = {
                "FCFS": lambda i: (procs[i][1], i),
                "SJF": lambda i: (procs[i][2], procs[i][1], i),
                "SRTF": lambda i: (rem[i], procs[i][1], i),
                "PRIORITY_NP": lambda i: (procs[i][3], procs[i][1], i),
                "PRIORITY_P": lambda i: (procs[i][3], procs[i][1], i),
            }[algo]
            preemptive = algo in ("SRTF", "PRIORITY_P")
            if running is not None and rem[running] == 0:
                running = None
            if ready and (running is None or preemptive):
                running = min(ready, key=key)
        if running is None:                         # idle
            t += 1
            continue
        if first[running] is None:
            first[running] = t
        rem[running] -= 1
        slice_left -= 1
        t += 1
        if rem[running] == 0:
            done[running] = t
    out = {}
    for i, (pid, a, b, _) in enumerate(procs):
        out[pid] = (done[i], done[i] - a, done[i] - a - b, first[i] - a)
    return out


def random_problem(rng: random.Random):
    n = rng.randint(2, 7)
    style = rng.choice(["zero", "staggered", "gaps", "ties"])
    if style == "zero":
        arr = [0] * n
    elif style == "staggered":
        arr = sorted(rng.randint(0, 10) for _ in range(n))
    elif style == "gaps":
        arr = sorted(rng.choice([0, 1, 2, 9, 10, 15, 22]) for _ in range(n))
    else:
        arr = [rng.choice([0, 2, 4]) for _ in range(n)]
    if rng.random() < 0.3:
        rng.shuffle(arr)                            # arrivals not in process order
    return [(f"P{i + 1}", arr[i], rng.randint(1, 12), rng.randint(1, 5)) for i in range(n)]


def check_invariants(res, algo) -> list[str]:
    errs = []
    busy = sum(s.end - s.start for s in res.gantt if s.pid != "IDLE")
    idle = sum(s.end - s.start for s in res.gantt if s.pid == "IDLE")
    if busy + idle != res.gantt[-1].end - res.gantt[0].start:
        errs.append("busy + idle != length")
    for pid, r in res.table.items():
        if r["waiting"] < 0:
            errs.append(f"{pid} WT < 0")
        if r["response"] > r["waiting"]:
            errs.append(f"{pid} RT > WT")
        if algo in ("FCFS", "SJF", "PRIORITY_NP") and r["response"] != r["waiting"]:
            errs.append(f"{pid} RT != WT in non-preemptive")
    return errs


def ostep_check(path: str, n: int, seed: int) -> tuple[int, int]:
    rng = random.Random(seed)
    ok = 0
    for _ in range(n):
        bursts = [rng.randint(1, 15) for _ in range(rng.randint(2, 6))]
        pol, q = rng.choice(["FIFO", "SJF", "RR"]), rng.randint(1, 5)
        out = subprocess.run([sys.executable, path, "-l", ",".join(map(str, bursts)), "-p", pol, "-q", str(q), "-c"],
                             capture_output=True, text=True).stdout
        rt, tat, wt = map(float, re.search(r"Average -- Response: ([\d.]+)\s+Turnaround ([\d.]+)\s+Wait ([\d.]+)",
                                           out).groups())
        algo = {"FIFO": "FCFS", "SJF": "SJF", "RR": "RR"}[pol]
        r = solve([Process(f"P{i + 1}", 0, b) for i, b in enumerate(bursts)], algo, q if algo == "RR" else None)
        ok += abs(r.avg_tat - tat) < 0.006 and abs(r.avg_wt - wt) < 0.006 and abs(r.avg_rt - rt) < 0.006
    return ok, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--ostep", help="path to OSTEP's cpu-sched/scheduler.py (optional)")
    args = ap.parse_args()
    rng = random.Random(args.seed)
    agree = inv_ok = 0
    per = {a: [0, 0] for a in ALGOS}
    first_fail = None
    for _ in range(args.n):
        procs = random_problem(rng)
        algo = rng.choice(ALGOS)
        q = rng.randint(1, 5) if algo == "RR" else None
        res = solve([Process(*p) for p in procs], algo, q)
        ref = tick_sim(procs, algo, q)
        mine = {pid: (r["completion"], r["turnaround"], r["waiting"], r["response"]) for pid, r in res.table.items()}
        same = mine == ref
        per[algo][0] += same
        per[algo][1] += 1
        agree += same
        if not same and first_fail is None:
            first_fail = (algo, q, procs, mine, ref)
        inv_ok += not check_invariants(res, algo)
    print(f"Engine vs independent tick simulator: {agree} / {args.n} problems identical")
    for a, (k, n) in per.items():
        print(f"  {a:12s} {k:5d} / {n}")
    print(f"Invariants hold: {inv_ok} / {args.n}")
    if first_fail:
        print("First disagreement:", first_fail)
    if args.ostep:
        ok, n = ostep_check(args.ostep, 3000, args.seed)
        print(f"Engine vs OSTEP scheduler.py (all arrive at 0): {ok} / {n}")
    return 0 if agree == args.n and inv_ok == args.n else 1


if __name__ == "__main__":
    sys.exit(main())

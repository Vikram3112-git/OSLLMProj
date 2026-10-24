"""
Solve a scheduling problem from the terminal with the exact engine (no LLM needed).

  python solve.py FCFS "P1 0 5, P2 1 3, P3 2 8"
  python solve.py RR "P1 0 5, P2 1 4, P3 2 2, P4 4 1" -q 2
  python solve.py PRIORITY_P "P1 0 4 3, P2 1 3 1, P3 2 2 4"      (4th number = priority)

Algorithms: FCFS, SJF, SRTF, PRIORITY_NP, PRIORITY_P, RR
"""
import argparse
import sys

from core.scheduler_engine import ALGORITHMS, Process, solve


def parse(text: str) -> list[Process]:
    procs = []
    for part in text.replace(";", ",").split(","):
        f = part.split()
        if not f:
            continue
        if len(f) not in (3, 4):
            sys.exit(f"Could not read '{part.strip()}'. Use: PID ARRIVAL BURST [PRIORITY]")
        procs.append(Process(f[0], int(f[1]), int(f[2]), int(f[3]) if len(f) == 4 else 0))
    return procs


def gantt_bar(res) -> str:
    """Draw the Gantt chart as three text lines: border, names, times."""
    cells = []
    for s in res.gantt:
        name = "idle" if s.pid == "IDLE" else s.pid
        width = max(len(name) + 2, 2 * (s.end - s.start))
        cells.append((name, width, s.end))
    top = "+" + "+".join("-" * w for _, w, _ in cells) + "+"
    mid = "|" + "|".join(n.center(w) for n, w, _ in cells) + "|"
    # each end time goes under the border after its block
    line, pos = [" "] * (len(top) + 4), 0
    line[0] = str(res.gantt[0].start)
    for _, w, end in cells:
        pos += w + 1
        for k, ch in enumerate(str(end)):
            if pos + k < len(line):
                line[pos + k] = ch
    return "\n".join([top, mid, top, "".join(line).rstrip()])


def main():
    ap = argparse.ArgumentParser(description="Solve a CPU scheduling problem exactly.")
    ap.add_argument("algorithm", type=str.upper, choices=list(ALGORITHMS))
    ap.add_argument("processes", help='e.g. "P1 0 5, P2 1 3"  (PID ARRIVAL BURST [PRIORITY])')
    ap.add_argument("-q", "--quantum", type=int, help="time quantum (Round Robin only)")
    args = ap.parse_args()
    if args.algorithm == "RR" and not args.quantum:
        sys.exit("Round Robin needs a time quantum, e.g. -q 2")

    res = solve(parse(args.processes), args.algorithm, args.quantum if args.algorithm == "RR" else None)
    title = ALGORITHMS[args.algorithm] + (f", q = {args.quantum}" if args.algorithm == "RR" else "")
    print(title)
    print("=" * len(title))
    print("\nScheduling decisions:")
    for s in res.steps:
        print(f"  t={s['time']:<3} ready [{s['ready']}] -> {s['runs']}")
    print("\nGantt chart:")
    print(gantt_bar(res))
    print()
    pr = args.algorithm.startswith("PRIORITY")
    head = ["PID", "AT", "BT"] + (["PR"] if pr else []) + ["CT", "TAT", "WT", "RT"]
    rows = [[pid, r["arrival"], r["burst"]] + ([r["priority"]] if pr else [])
            + [r["completion"], r["turnaround"], r["waiting"], r["response"]] for pid, r in res.table.items()]
    print("  ".join(f"{h:>4}" for h in head))
    for row in rows:
        print("  ".join(f"{str(v):>4}" for v in row))
    print(f"\nAverage TAT = {res.avg_tat:.2f}   Average WT = {res.avg_wt:.2f}   Average RT = {res.avg_rt:.2f}")
    print(f"Throughput = {res.throughput:.3f} processes/unit   CPU utilisation = {res.cpu_utilization:.0%}")


if __name__ == "__main__":
    main()

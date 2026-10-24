"""
Check the non-scheduling solvers (core/os_solvers.py) against independent reference methods.

  page replacement : FIFO with a deque, LRU with an ordered dict, and OPT against an exhaustive
                     search for the true minimum number of faults
  Banker's         : safe / unsafe against trying every possible order of the processes
  deadlock detect  : the same exhaustive search with the Request matrix
  disk scheduling  : closed formulas for the total head movement, and SSTF's greedy property
  memory allocation: a separate straightforward implementation

Run:  python finetune/verify_solvers.py [--n 2000]
"""
import argparse
import itertools
import random
import sys
from collections import OrderedDict, deque
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.os_solvers import allocate, bankers, deadlock_detect, disk, page_replacement  # noqa: E402


# ------------------------------------------------------------------ page replacement
def ref_fifo(refs, f):
    q, s, faults = deque(), set(), 0
    for p in refs:
        if p in s:
            continue
        faults += 1
        if len(q) == f:
            s.discard(q.popleft())
        q.append(p); s.add(p)
    return faults


def ref_lru(refs, f):
    od, faults = OrderedDict(), 0
    for p in refs:
        if p in od:
            od.move_to_end(p); continue
        faults += 1
        if len(od) == f:
            od.popitem(last=False)
        od[p] = True
    return faults


def ref_min_faults(refs, f):
    """Exhaustive search over every eviction choice: the true minimum."""
    refs = tuple(refs)

    @lru_cache(maxsize=None)
    def go(t, mem):
        if t == len(refs):
            return 0
        p = refs[t]
        if p in mem:
            return go(t + 1, mem)
        if len(mem) < f:
            return 1 + go(t + 1, mem | {p})
        return 1 + min(go(t + 1, (mem - {v}) | {p}) for v in mem)
    return go(0, frozenset())


# ------------------------------------------------------------------ Banker's / detection
def ref_safe(alloc, need, avail, finished=None):
    n = len(alloc)
    start = [i for i in range(n) if not (finished and finished[i])]
    for perm in itertools.permutations(start):
        work, ok = list(avail), True
        for i in perm:
            if any(need[i][j] > work[j] for j in range(len(work))):
                ok = False; break
            work = [w + a for w, a in zip(work, alloc[i])]
        if ok:
            return True
    return not start


def valid_sequence(seq, procs, alloc, need, avail):
    work = list(avail)
    for p in seq:
        i = procs.index(p)
        if any(need[i][j] > work[j] for j in range(len(work))):
            return False
        work = [w + a for w, a in zip(work, alloc[i])]
    return sorted(seq) == sorted(procs)


# ------------------------------------------------------------------ disk
def ref_disk_total(req, head, algo, maxc, direction):
    lo, hi = min(req), max(req)
    if algo == "D_FCFS":
        pos, t = head, 0
        for r in req:
            t += abs(r - pos); pos = r
        return t
    if direction == "down":   # mirror the disk so every case is "up"
        req = [maxc - r for r in req]; head = maxc - head; lo, hi = min(req), max(req)
    below = [r for r in req if r < head]
    above = [r for r in req if r >= head]
    if algo == "SCAN":
        return (hi - head) if not below else (maxc - head) + (maxc - min(below))
    if algo == "LOOK":
        return (hi - head) if not below else (max(above, default=head) - head) + (max(above, default=head) - min(below))
    if algo == "C-SCAN":
        return (hi - head) if not below else (maxc - head) + maxc + max(below)
    if algo == "C-LOOK":
        top = max(above, default=head)
        return (hi - head) if not below else (top - head) + (top - min(below)) + (max(below) - min(below))
    raise ValueError(algo)


def sstf_is_greedy(req, head, order):
    pending, pos = list(req), head
    for r in order:
        if abs(r - pos) != min(abs(x - pos) for x in pending):
            return False
        pending.remove(r); pos = r
    return not pending


# ------------------------------------------------------------------ memory allocation
def ref_alloc(blocks, sizes, algo):
    holes, out, last = list(blocks), [], 0
    for s in sizes:
        cand = [i for i in range(len(holes)) if holes[i] >= s]
        if not cand:
            out.append(None); continue
        if algo == "FIRST":
            i = cand[0]
        elif algo == "BEST":
            i = sorted(cand, key=lambda k: (holes[k], k))[0]
        elif algo == "WORST":
            i = sorted(cand, key=lambda k: (-holes[k], k))[0]
        else:
            order = list(range(last, len(holes))) + list(range(0, last))
            i = [k for k in order if holes[k] >= s][0]
        holes[i] -= s; last = i; out.append(f"B{i + 1}")
    return out, holes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    res = {}

    def tally(name, ok):
        k = res.setdefault(name, [0, 0]); k[0] += bool(ok); k[1] += 1

    for _ in range(a.n):
        refs = [rng.randint(0, rng.choice([4, 6, 8])) for _ in range(rng.randint(6, 14))]
        f = rng.randint(2, 4)
        tally("Page FIFO vs deque", page_replacement(refs, f, "FIFO").view["faults"] == ref_fifo(refs, f))
        tally("Page LRU vs ordered dict", page_replacement(refs, f, "LRU").view["faults"] == ref_lru(refs, f))
        tally("Page OPT vs exhaustive minimum", page_replacement(refs, f, "OPT").view["faults"] == ref_min_faults(refs, f))

        n, m = rng.randint(3, 6), rng.randint(2, 4)
        procs = [f"P{i}" for i in range(n)]
        mx = [[rng.randint(0, 8) for _ in range(m)] for _ in range(n)]
        al = [[rng.randint(0, x) for x in row] for row in mx]
        av = [rng.randint(0, 5) for _ in range(m)]
        need = [[x - y for x, y in zip(r1, r2)] for r1, r2 in zip(mx, al)]
        b = bankers(procs, [chr(65 + j) for j in range(m)], al, mx, av)
        tally("Banker's safe/unsafe vs all orders", b.view["safe"] == ref_safe(al, need, av))
        if b.view["safe"]:
            tally("Banker's safe sequence is valid", valid_sequence(b.view["sequence"], procs, al, need, av))
        rq = [[rng.randint(0, 4) for _ in range(m)] for _ in range(n)]
        d = deadlock_detect(procs, [chr(65 + j) for j in range(m)], al, rq, av)
        zero = [all(x == 0 for x in row) for row in al]
        tally("Deadlock detection vs all orders", (not d.view["deadlocked"]) == ref_safe(al, rq, av, zero))

        maxc = rng.choice([99, 199, 499])
        req = rng.sample(range(0, maxc + 1), rng.randint(4, 9))
        head = rng.randint(0, maxc)
        direction = rng.choice(["up", "down"])
        for algo in ["D_FCFS", "SCAN", "LOOK", "C-SCAN", "C-LOOK"]:
            r = disk(req, head, algo, maxc, direction)
            tally(f"Disk {algo.replace('D_', '')} total vs formula",
                  r.view["total"] == ref_disk_total(req, head, algo, maxc, direction)
                  and sorted(r.view["order"]) == sorted(req))
        s = disk(req, head, "SSTF", maxc)
        tally("Disk SSTF greedy property", sstf_is_greedy(req, head, s.view["order"]))

        blocks = [rng.randint(5, 60) * 10 for _ in range(rng.randint(3, 6))]
        sizes = [rng.randint(3, 50) * 10 for _ in range(rng.randint(3, 6))]
        for algo in ["FIRST", "BEST", "WORST", "NEXT"]:
            r = allocate(blocks, sizes, algo)
            want, holes = ref_alloc(blocks, sizes, algo)
            got = [r.view["placed"][f"P{i + 1}"] for i in range(len(sizes))]
            tally(f"Memory {algo.title()} fit vs reference", got == want and r.view["holes_after"] == holes)

    width = max(len(k) for k in res)
    allok = True
    for k, (ok, tot) in res.items():
        allok &= ok == tot
        print(f"{k:{width}s}  {ok} / {tot}")
    print("all identical" if allok else "MISMATCHES FOUND")
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())

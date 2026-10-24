"""
Exact solvers for the numerical parts of the OS syllabus outside CPU scheduling.

  bankers  : Banker's algorithm (safety, resource request) and deadlock detection
  page     : page replacement - FIFO, LRU, OPT (optimal)
  disk     : disk scheduling - FCFS, SSTF, SCAN, C-SCAN, LOOK, C-LOOK
  alloc    : contiguous memory allocation - first, best, worst, next fit

Like the CPU scheduling engine, every solver records each decision and the reason for it, so the
language model only has to explain numbers that are already correct. Course conventions are fixed
here and stated in every trace:

  * Banker's safety check: repeated passes over P0..Pn-1 in order; in each pass every unfinished
    process whose Need <= Work runs. Any order that satisfies the check is a valid safe sequence.
  * Page replacement: frames are filled left to right; OPT replaces the page used farthest in the
    future, and among pages never used again the one loaded earliest.
  * Disk: SSTF ties go to the request that comes first in the queue; SCAN and C-SCAN travel to the
    disk edge; the C-SCAN / C-LOOK return jump IS counted in the total head movement.
  * Memory: a chosen hole is split and the remainder stays available; next fit resumes its search at
    the hole used last (which may still have room).
"""
from __future__ import annotations

from dataclasses import dataclass, field

NAMES = {
    "BANKERS": "Banker's algorithm (safety check)", "REQUEST": "Banker's algorithm (resource request)",
    "DETECT": "Deadlock detection",
    "FIFO": "FIFO page replacement", "LRU": "LRU page replacement", "OPT": "Optimal (OPT) page replacement",
    "D_FCFS": "FCFS disk scheduling", "SSTF": "SSTF disk scheduling", "SCAN": "SCAN (elevator) disk scheduling",
    "C-SCAN": "C-SCAN disk scheduling", "LOOK": "LOOK disk scheduling", "C-LOOK": "C-LOOK disk scheduling",
    "FIRST": "First fit", "BEST": "Best fit", "WORST": "Worst fit", "NEXT": "Next fit",
}
KIND_ALGOS = {
    "bankers": ["BANKERS", "REQUEST", "DETECT"],
    "page": ["FIFO", "LRU", "OPT"],
    "disk": ["D_FCFS", "SSTF", "SCAN", "C-SCAN", "LOOK", "C-LOOK"],
    "alloc": ["FIRST", "BEST", "WORST", "NEXT"],
}
SHORT = {"D_FCFS": "FCFS", "FIRST": "First fit", "BEST": "Best fit", "WORST": "Worst fit", "NEXT": "Next fit",
         "BANKERS": "Safety", "REQUEST": "Request", "DETECT": "Detection"}


def kind_of(algo: str) -> str:
    return next(k for k, v in KIND_ALGOS.items() if algo in v)


@dataclass
class Solved:
    kind: str
    algorithm: str
    inputs: dict
    steps: list = field(default_factory=list)      # each {"text": "...", ...extra for the view}
    summary: dict = field(default_factory=dict)
    view: dict = field(default_factory=dict)       # everything the web page needs to draw it

    @property
    def name(self) -> str:
        return NAMES[self.algorithm]

    def steps_text(self) -> str:
        return "\n".join(s["text"] for s in self.steps)

    def summary_text(self) -> str:
        return "\n".join(f"{k}: {v}" for k, v in self.summary.items())

    def problem_text(self) -> str:
        return problem_text(self.kind, self.algorithm, self.inputs)

    def to_dict(self) -> dict:
        return {"kind": self.kind, "algorithm": self.algorithm, "name": self.name, "inputs": self.inputs,
                "steps": self.steps, "summary": self.summary, "view": self.view}


def _vec(v) -> str:
    return "(" + ", ".join(str(x) for x in v) + ")"


def problem_text(kind: str, algo: str, inp: dict) -> str:
    """The problem statement as plain text (for prompts and the dataset)."""
    if kind == "bankers":
        r = inp["resources"]
        rows = [f"{p}: Allocation {_vec(a)}  " + ("Request " if algo == "DETECT" else "Max ") + _vec(m)
                for p, a, m in zip(inp["processes"], inp["allocation"],
                                   inp["request_matrix"] if algo == "DETECT" else inp["max"])]
        s = f"Resource types {', '.join(r)}; Available {_vec(inp['available'])}\n" + "\n".join(rows)
        if algo == "REQUEST":
            s += f"\nRequest by {inp['request_pid']}: {_vec(inp['request'])}"
        return s
    if kind == "page":
        return f"Reference string: {' '.join(map(str, inp['refs']))}\nNumber of frames: {inp['frames']}"
    if kind == "disk":
        s = (f"Request queue: {', '.join(map(str, inp['requests']))}\nHead starts at {inp['head']}; "
             f"cylinders 0 to {inp['max_cyl']}")
        if algo in ("SCAN", "C-SCAN", "LOOK", "C-LOOK"):
            s += f"; head moving towards {'larger' if inp['direction'] == 'up' else 'smaller'} cylinder numbers"
        return s
    if kind == "alloc":
        return (f"Memory holes (in order): {', '.join(f'{b} KB' for b in inp['blocks'])}\n"
                f"Processes (in order): {', '.join(f'{p} = {s} KB' for p, s in zip(inp['names'], inp['sizes']))}")
    raise ValueError(kind)


# ======================================================================= Banker's algorithm
def _safety(processes, need, alloc, work, finish=None, names=None):
    """Repeated passes in process order. Returns (sequence, steps, finish, work)."""
    n, m = len(processes), len(work)
    work = list(work)
    finish = list(finish) if finish else [False] * n
    seq, steps, passno = [], [], 0
    progress = True
    while progress and not all(finish):
        progress, passno = False, passno + 1
        for i in range(n):
            if finish[i]:
                continue
            ok = all(need[i][j] <= work[j] for j in range(m))
            if ok:
                new = [work[j] + alloc[i][j] for j in range(m)]
                steps.append({"text": f"Pass {passno}: {processes[i]} needs {_vec(need[i])} <= Work {_vec(work)}, so "
                                      f"it can finish and releases {_vec(alloc[i])}. Work becomes {_vec(new)}.",
                              "pid": processes[i], "need": need[i], "work_before": work, "work_after": new, "ok": True,
                              "pass": passno})
                work, finish[i], progress = new, True, True
                seq.append(processes[i])
            else:
                short = [names[j] if names else chr(65 + j) for j in range(m) if need[i][j] > work[j]]
                steps.append({"text": f"Pass {passno}: {processes[i]} needs {_vec(need[i])}, which is more than Work "
                                      f"{_vec(work)} for resource(s) {', '.join(short)}, so it "
                                      f"must wait.", "pid": processes[i], "need": need[i], "work_before": work,
                              "work_after": work, "ok": False, "pass": passno})
    return seq, steps, finish, work


def bankers(processes, resources, allocation, maximum, available) -> Solved:
    need = [[mx - a for mx, a in zip(mrow, arow)] for mrow, arow in zip(maximum, allocation)]
    if any(x < 0 for row in need for x in row):
        raise ValueError("Max must be at least Allocation for every process and resource.")
    seq, steps, finish, work = _safety(processes, need, allocation, available, names=resources)
    safe = all(finish)
    steps.insert(0, {"text": "Need = Max - Allocation for every process: " +
                     "; ".join(f"{p} {_vec(nr)}" for p, nr in zip(processes, need)) + f". Work starts as Available "
                     f"{_vec(available)}. Convention: repeated passes over the processes in order."})
    stuck = [p for p, f in zip(processes, finish) if not f]
    steps.append({"text": (f"All processes can finish, so the system is in a SAFE state. Safe sequence: <{', '.join(seq)}>."
                           if safe else f"No remaining process can be satisfied ({', '.join(stuck)}), so the system is "
                           f"UNSAFE (a deadlock may occur).")})
    inp = {"processes": processes, "resources": resources, "allocation": allocation, "max": maximum,
           "available": available}
    summary = {"Need matrix": "; ".join(f"{p} {_vec(n)}" for p, n in zip(processes, need)),
               "State": "safe" if safe else "unsafe", "Safe sequence": f"<{', '.join(seq)}>" if safe else "none",
               "Final Work": _vec(work)}
    view = {"need": need, "sequence": seq, "safe": safe, "rows": [s for s in steps if "pid" in s]}
    return Solved("bankers", "BANKERS", inp, steps, summary, view)


def bankers_request(processes, resources, allocation, maximum, available, pid, request) -> Solved:
    i = processes.index(pid)
    need = [[mx - a for mx, a in zip(mrow, arow)] for mrow, arow in zip(maximum, allocation)]
    inp = {"processes": processes, "resources": resources, "allocation": allocation, "max": maximum,
           "available": available, "request_pid": pid, "request": request}
    steps = [{"text": f"Need of {pid} = Max - Allocation = {_vec(need[i])}."}]
    if any(r > n for r, n in zip(request, need[i])):
        steps.append({"text": f"Request {_vec(request)} > Need {_vec(need[i])}: error, {pid} asked for more than its "
                              f"declared maximum. The request is refused."})
        return Solved("bankers", "REQUEST", inp, steps, {"Decision": "refused (exceeds Need)"},
                      {"need": need, "granted": False, "reason": "exceeds need"})
    steps.append({"text": f"Step 1: Request {_vec(request)} <= Need {_vec(need[i])}: OK."})
    if any(r > a for r, a in zip(request, available)):
        steps.append({"text": f"Step 2: Request {_vec(request)} > Available {_vec(available)}: {pid} must wait, the "
                              f"resources are not free now."})
        return Solved("bankers", "REQUEST", inp, steps, {"Decision": "wait (not enough available)"},
                      {"need": need, "granted": False, "reason": "not available"})
    steps.append({"text": f"Step 2: Request {_vec(request)} <= Available {_vec(available)}: OK."})
    avail2 = [a - r for a, r in zip(available, request)]
    alloc2 = [row[:] for row in allocation]
    need2 = [row[:] for row in need]
    alloc2[i] = [a + r for a, r in zip(alloc2[i], request)]
    need2[i] = [n - r for n, r in zip(need2[i], request)]
    steps.append({"text": f"Step 3: pretend to grant it. Available becomes {_vec(avail2)}, Allocation of {pid} becomes "
                          f"{_vec(alloc2[i])}, Need of {pid} becomes {_vec(need2[i])}. Now run the safety check."})
    seq, ssteps, finish, work = _safety(processes, need2, alloc2, avail2, names=resources)
    steps += ssteps
    safe = all(finish)
    steps.append({"text": (f"The new state is SAFE (<{', '.join(seq)}>), so the request is GRANTED." if safe else
                           "The new state would be UNSAFE, so the request is NOT granted; "
                           f"{pid} waits and the old state is restored.")})
    summary = {"Decision": "granted" if safe else "not granted (unsafe)",
               "Safe sequence after granting": f"<{', '.join(seq)}>" if safe else "none"}
    view = {"need": need, "need_after": need2, "available_after": avail2, "granted": safe, "sequence": seq,
            "rows": [s for s in ssteps if "pid" in s]}
    return Solved("bankers", "REQUEST", inp, steps, summary, view)


def deadlock_detect(processes, resources, allocation, request_matrix, available) -> Solved:
    n = len(processes)
    finish = [all(a == 0 for a in allocation[i]) for i in range(n)]
    steps = [{"text": "Detection algorithm: Work = Available; a process holding no resources is marked finished. "
                      "A process can finish if its Request <= Work."}]
    seq, ssteps, finish, work = _safety(processes, request_matrix, allocation, available, finish, names=resources)
    steps += [dict(s, text=s["text"].replace("needs", "requests")) for s in ssteps]
    dead = [p for p, f in zip(processes, finish) if not f]
    steps.append({"text": ("No deadlock: every process can finish." if not dead else
                           f"Deadlock: {', '.join(dead)} can never finish.")})
    inp = {"processes": processes, "resources": resources, "allocation": allocation,
           "request_matrix": request_matrix, "available": available}
    return Solved("bankers", "DETECT", inp, steps,
                  {"Deadlocked": ", ".join(dead) if dead else "none", "Completion order": f"<{', '.join(seq)}>"},
                  {"deadlocked": dead, "sequence": seq, "rows": [s for s in ssteps if "pid" in s]})


# ======================================================================= page replacement
def page_replacement(refs, frames, algorithm) -> Solved:
    slots = [None] * frames
    loaded_at, last_used = {}, {}
    steps, faults, fifo_order = [], 0, []
    for t, page in enumerate(refs):
        if page in slots:
            last_used[page] = t
            steps.append({"text": f"t={t + 1}: {page} is already in memory, HIT. Frames {_frames(slots)}.",
                          "ref": page, "frames": slots[:], "fault": False, "victim": None})
            continue
        faults += 1
        if None in slots:
            k = slots.index(None)
            why = f"a free frame is available (frame {k + 1})"
            victim = None
        else:
            if algorithm == "FIFO":
                victim = fifo_order[0]
                why = f"{victim} has been in memory the longest (loaded first)"
            elif algorithm == "LRU":
                victim = min(slots, key=lambda p: last_used[p])
                why = f"{victim} was used least recently (last at t={last_used[victim] + 1})"
            else:  # OPT
                future = refs[t + 1:]
                def next_use(p):
                    return future.index(p) if p in future else float("inf")
                never = [p for p in slots if next_use(p) == float("inf")]
                if never:
                    victim = min(never, key=lambda p: loaded_at[p])
                    why = (f"{victim} is never used again" if len(never) == 1 else
                           f"{', '.join(map(str, never))} are never used again; {victim} was loaded earliest")
                else:
                    victim = max(slots, key=next_use)
                    why = f"{victim} is used farthest in the future (at t={t + 2 + next_use(victim)})"
            k = slots.index(victim)
            fifo_order.remove(victim)
        slots[k] = page
        fifo_order.append(page)
        loaded_at[page] = t
        last_used[page] = t
        steps.append({"text": f"t={t + 1}: {page} is not in memory, PAGE FAULT {faults}. "
                              + (f"Replace {victim} because {why}." if victim is not None else f"Load it: {why}.")
                              + f" Frames {_frames(slots)}.",
                      "ref": page, "frames": slots[:], "fault": True, "victim": victim})
    hits = len(refs) - faults
    summary = {"Page faults": faults, "Page hits": hits, "Hit ratio": f"{hits}/{len(refs)} = {hits / len(refs):.2%}",
               "Fault ratio": f"{faults}/{len(refs)} = {faults / len(refs):.2%}"}
    return Solved("page", algorithm, {"refs": list(refs), "frames": frames}, steps, summary,
                  {"faults": faults, "hits": hits, "columns": [{"ref": s["ref"], "frames": s["frames"],
                                                               "fault": s["fault"], "victim": s["victim"]} for s in steps]})


def _frames(slots) -> str:
    return "[" + " ".join("-" if s is None else str(s) for s in slots) + "]"


# ======================================================================= disk scheduling
def disk(requests, head, algorithm, max_cyl=199, direction="up") -> Solved:
    pending = list(requests)
    order, pos, steps, total = [], head, [], 0
    jumps = []

    def move(to, why, service=True):
        nonlocal pos, total
        d = abs(to - pos)
        total += d
        steps.append({"text": f"{pos} -> {to}: {d} cylinder{'' if d == 1 else 's'} ({why}). Total so far {total}.",
                      "from": pos, "to": to, "dist": d, "service": service})
        pos = to
        if service:
            order.append(to)

    if algorithm == "D_FCFS":
        for r in pending:
            move(r, "next request in arrival order")
    elif algorithm == "SSTF":
        while pending:
            best = min(range(len(pending)), key=lambda i: (abs(pending[i] - pos), i))
            r = pending.pop(best)
            move(r, f"closest pending request, {abs(r - pos)} away")
    else:
        up = sorted(r for r in pending if r >= head)
        down = sorted((r for r in pending if r < head), reverse=True)
        if direction == "down":
            up, down = sorted((r for r in pending if r <= head), reverse=True), sorted(r for r in pending if r > head)
        first, second = up, down
        edge = max_cyl if direction == "up" else 0
        other_edge = 0 if direction == "up" else max_cyl
        word = "upwards" if direction == "up" else "downwards"
        for r in first:
            move(r, f"next request while moving {word}")
        if algorithm == "SCAN":
            if second and pos != edge:
                move(edge, "SCAN continues to the end of the disk before reversing", service=False)
            for r in second:
                move(r, "next request after reversing")
        elif algorithm == "LOOK":
            for r in second:
                move(r, "LOOK reverses at the last request; next request after reversing")
        elif algorithm == "C-SCAN":
            if second:
                if pos != edge:
                    move(edge, "C-SCAN continues to the end of the disk", service=False)
                move(other_edge, "jump back to the other end (counted in the total)", service=False)
                jumps.append(len(steps) - 1)
                second = sorted(second) if direction == "up" else sorted(second, reverse=True)
                for r in second:
                    move(r, f"next request, moving {word} again")
        elif algorithm == "C-LOOK":
            if second:
                second = sorted(second) if direction == "up" else sorted(second, reverse=True)
                move(second[0], "jump back to the farthest request on the other side (counted in the total)")
                jumps.append(len(steps) - 1)
                for r in second[1:]:
                    move(r, f"next request, moving {word} again")
    seek = total / len(requests) if requests else 0
    summary = {"Service order": " -> ".join(map(str, order)), "Total head movement": f"{total} cylinders",
               "Average seek distance": f"{total}/{len(requests)} = {seek:.2f} cylinders"}
    inp = {"requests": list(requests), "head": head, "max_cyl": max_cyl, "direction": direction}
    return Solved("disk", algorithm, inp, steps, summary,
                  {"path": [head] + [s["to"] for s in steps], "service": [s["service"] for s in steps],
                   "total": total, "order": order, "jumps": jumps})


# ======================================================================= memory allocation
def allocate(blocks, sizes, algorithm, names=None) -> Solved:
    names = names or [f"P{i + 1}" for i in range(len(sizes))]
    holes = list(blocks)
    steps, placed, last = [], {}, 0
    labels = [f"B{i + 1}" for i in range(len(blocks))]
    for p, s in zip(names, sizes):
        fits = [i for i, h in enumerate(holes) if h >= s]
        if not fits:
            steps.append({"text": f"{p} ({s} KB): no hole is big enough (largest is {max(holes)} KB), so {p} must "
                                  f"wait.", "pid": p, "size": s, "block": None, "holes": holes[:]})
            placed[p] = None
            continue
        if algorithm == "FIRST":
            i, why = fits[0], "first hole from the start that is large enough"
        elif algorithm == "BEST":
            i = min(fits, key=lambda k: (holes[k], k)); why = "smallest hole that is large enough"
        elif algorithm == "WORST":
            i = max(fits, key=lambda k: (holes[k], -k)); why = "largest hole"
        else:  # NEXT: continue after the last hole used
            n = len(holes)
            i = next(k % n for k in range(last, last + n) if holes[k % n] >= s)
            why = "first hole large enough, searching on from the hole used last"
        before = holes[i]
        holes[i] -= s
        last = i
        placed[p] = labels[i]
        steps.append({"text": f"{p} ({s} KB) -> {labels[i]} ({before} KB): {why}. {holes[i]} KB of that hole stays "
                              f"free. Holes now {', '.join(f'{h}' for h in holes)}.",
                      "pid": p, "size": s, "block": labels[i], "before": before, "after": holes[i], "holes": holes[:]})
    waiting = [p for p, b in placed.items() if b is None]
    summary = {"Placement": ", ".join(f"{p} -> {b or 'waits'}" for p, b in placed.items()),
               "Free holes left": ", ".join(f"{labels[i]} {h} KB" for i, h in enumerate(holes)),
               "Total free memory": f"{sum(holes)} KB", "Processes that must wait": ", ".join(waiting) or "none"}
    if waiting:
        summary["External fragmentation"] = (f"{sum(holes)} KB is free in total but split into holes too small for "
                                             f"{', '.join(waiting)}" if sum(holes) >= min(s for p, s in zip(names, sizes)
                                                                                          if p in waiting) else
                                             "not enough free memory in total")
    inp = {"blocks": list(blocks), "sizes": list(sizes), "names": names}
    return Solved("alloc", algorithm, inp, steps, summary,
                  {"labels": labels, "placed": placed, "holes_after": holes, "waiting": waiting})


# ======================================================================= one entry point
def solve_any(algorithm: str, inputs: dict) -> Solved:
    k = kind_of(algorithm)
    if k == "bankers":
        if algorithm == "BANKERS":
            return bankers(inputs["processes"], inputs["resources"], inputs["allocation"], inputs["max"],
                           inputs["available"])
        if algorithm == "REQUEST":
            return bankers_request(inputs["processes"], inputs["resources"], inputs["allocation"], inputs["max"],
                                   inputs["available"], inputs["request_pid"], inputs["request"])
        return deadlock_detect(inputs["processes"], inputs["resources"], inputs["allocation"],
                               inputs["request_matrix"], inputs["available"])
    if k == "page":
        return page_replacement(inputs["refs"], inputs["frames"], algorithm)
    if k == "disk":
        return disk(inputs["requests"], inputs["head"], algorithm, inputs.get("max_cyl", 199),
                    inputs.get("direction", "up"))
    return allocate(inputs["blocks"], inputs["sizes"], algorithm, inputs.get("names"))

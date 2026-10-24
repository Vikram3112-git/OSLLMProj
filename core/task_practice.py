"""
Practice questions for Banker's algorithm, page replacement, disk scheduling and memory allocation:
what to ask, how to check the answer exactly, and step-by-step hints taken from the solver's trace.
"""
from __future__ import annotations

import re

from config import NUMERICAL_TOPICS
from core.os_solvers import Solved, kind_of


def task_topic(algo: str) -> str:
    return next(t for t, algos in NUMERICAL_TOPICS.items() if algo in algos)


def ask_fields(s: Solved) -> list[dict]:
    if s.kind == "page":
        return [{"key": "faults", "label": "Number of page faults", "type": "int"},
                {"key": "hits", "label": "Number of page hits", "type": "int"}]
    if s.kind == "disk":
        return [{"key": "order", "label": "Service order (cylinders, comma separated)", "type": "list"},
                {"key": "total", "label": "Total head movement (cylinders)", "type": "int"}]
    if s.kind == "alloc":
        return [{"key": f"place_{p}", "label": f"Hole for {p} ({sz} KB): e.g. B2, or 'wait'", "type": "text"}
                for p, sz in zip(s.inputs["names"], s.inputs["sizes"])]
    if s.algorithm == "BANKERS":
        return [{"key": "safe", "label": "Is the system in a safe state?", "type": "choice", "options": ["yes", "no"]},
                {"key": "sequence", "label": "A safe sequence if safe (e.g. P1, P3, P4, P0, P2)", "type": "list"}]
    if s.algorithm == "REQUEST":
        return [{"key": "decision", "label": f"Can {s.inputs['request_pid']}'s request be granted now?",
                 "type": "choice", "options": ["grant", "wait", "refuse"]}]
    return [{"key": "deadlocked", "label": "Deadlocked processes (comma separated, or 'none')", "type": "list"}]


def _list(v) -> list[str]:
    if isinstance(v, list):
        items = v
    else:
        items = re.split(r"[\s,>;-]+", str(v or ""))
    return [x.strip().upper() for x in items if x and x.strip()]


def _int(v):
    try:
        return int(float(str(v).strip()))
    except (TypeError, ValueError):
        return None


def _valid_safe_sequence(seq: list[str], s: Solved) -> bool:
    inp = s.inputs
    procs = [p.upper() for p in inp["processes"]]
    if sorted(seq) != sorted(procs):
        return False
    need = [[m - a for m, a in zip(mr, ar)] for mr, ar in zip(inp["max"], inp["allocation"])]
    work = list(inp["available"])
    for p in seq:
        i = procs.index(p)
        if any(n > w for n, w in zip(need[i], work)):
            return False
        work = [w + a for w, a in zip(work, inp["allocation"][i])]
    return True


def check(s: Solved, answers: dict) -> dict:
    """Exact checking. Returns score 0..1, which fields were right, mistakes (for the profile) and feedback."""
    ok: dict[str, bool] = {}
    mistakes, notes = [], []
    if s.kind == "page":
        f, h = _int(answers.get("faults")), _int(answers.get("hits"))
        ok["faults"] = f == s.view["faults"]
        ok["hits"] = h == s.view["hits"]
        if not ok["faults"]:
            mistakes.append(f"{s.algorithm} victim choice")
            notes.append(f"There are {s.view['faults']} page faults, not {f}. Check each replacement against the rule.")
        if not ok["hits"]:
            notes.append(f"Hits = references - faults = {len(s.inputs['refs'])} - {s.view['faults']} = {s.view['hits']}.")
    elif s.kind == "disk":
        order = [_int(x) for x in _list(answers.get("order"))]
        total = _int(answers.get("total"))
        ok["order"] = order == s.view["order"]
        ok["total"] = total == s.view["total"]
        if not ok["order"]:
            mistakes.append(f"{s.algorithm} service order")
            notes.append(f"The service order is {' -> '.join(map(str, s.view['order']))}.")
        if not ok["total"]:
            mistakes.append("total head movement")
            notes.append(f"Total head movement is {s.view['total']}: add |next - current| for every move"
                         + (", including the return jump" if s.algorithm in ("C-SCAN", "C-LOOK") else "")
                         + (" and the move to the disk edge" if s.algorithm in ("SCAN", "C-SCAN") else "") + ".")
    elif s.kind == "alloc":
        for p in s.inputs["names"]:
            want = s.view["placed"][p] or "WAIT"
            got = str(answers.get(f"place_{p}", "")).strip().upper().replace(" ", "")
            got = "WAIT" if got in ("WAIT", "WAITS", "NONE", "-", "NOTALLOCATED") else got
            ok[f"place_{p}"] = got == want
            if got != want:
                notes.append(f"{p} goes to {want.title() if want == 'WAIT' else want}, not {got or '(blank)'}.")
        if not all(ok.values()):
            mistakes.append(f"{s.name.lower()} choice")
    elif s.algorithm == "BANKERS":
        safe = str(answers.get("safe", "")).strip().lower().startswith("y")
        ok["safe"] = safe == s.view["safe"]
        if s.view["safe"]:
            seq = _list(answers.get("sequence"))
            ok["sequence"] = _valid_safe_sequence(seq, s)
            if not ok["sequence"]:
                mistakes.append("safe sequence")
                notes.append(f"<{', '.join(seq) or 'blank'}> is not a valid safe sequence; one valid sequence is "
                             f"<{', '.join(s.view['sequence'])}> (any order that passes the check counts).")
        if not ok["safe"]:
            mistakes.append("safety check")
            notes.append(f"The state is {'safe' if s.view['safe'] else 'unsafe'}. Start from Work = Available and "
                         "compare each Need with Work.")
    elif s.algorithm == "REQUEST":
        want = "grant" if s.view["granted"] else ("refuse" if s.view.get("reason") == "exceeds need" else "wait")
        got = str(answers.get("decision", "")).strip().lower()
        ok["decision"] = got == want
        if not ok["decision"]:
            mistakes.append("resource-request algorithm")
            notes.append(f"The answer is '{want}': {s.summary['Decision']}.")
    else:
        got = sorted(x for x in _list(answers.get("deadlocked")) if x != "NONE")
        ok["deadlocked"] = got == sorted(p.upper() for p in s.view["deadlocked"])
        if not ok["deadlocked"]:
            mistakes.append("deadlock detection")
            notes.append(f"Deadlocked: {', '.join(s.view['deadlocked']) or 'none'}.")
    score = sum(ok.values()) / len(ok) if ok else 0.0
    feedback = "All correct. " if score == 1 else " ".join(notes)
    return {"score": score, "fields": ok, "mistakes": mistakes, "feedback": feedback.strip()}


def hint(s: Solved, level: int) -> str:
    """Hint 1: the rule. Hint 2: the first decisions. Hint 3: almost the whole trace, without the final numbers."""
    rule = {
        "FIFO": "Replace the page that has been in memory the longest.",
        "LRU": "Replace the page whose last use is furthest in the past.",
        "OPT": "Replace the page whose next use is furthest in the future (or never comes).",
        "D_FCFS": "Serve the requests in the order they arrived.",
        "SSTF": "Always move to the closest pending request.",
        "SCAN": "Move in the current direction serving requests up to the disk edge, then reverse.",
        "C-SCAN": "Move in one direction to the edge, jump to the other end, and continue in the same direction.",
        "LOOK": "Like SCAN, but reverse at the last request instead of the disk edge.",
        "C-LOOK": "Like C-SCAN, but jump from the last request to the farthest request on the other side.",
        "FIRST": "Take the first hole from the start that is large enough.",
        "BEST": "Take the smallest hole that is large enough.",
        "WORST": "Take the largest hole.",
        "NEXT": "Like first fit, but start searching at the hole used last.",
        "BANKERS": "Compute Need = Max - Allocation, start with Work = Available, and find a process with Need <= Work.",
        "REQUEST": "Check Request <= Need, then Request <= Available, then pretend to grant it and run the safety check.",
        "DETECT": "Like the safety check, but compare Request (not Need) with Work.",
    }[s.algorithm]
    steps = [st["text"] for st in s.steps]
    if level <= 1:
        return rule
    if level == 2:
        return " ".join(steps[:2]) if s.kind != "bankers" else " ".join(steps[:3])
    cut = max(1, len(steps) - 1)
    return " ".join(steps[:cut])

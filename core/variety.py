"""
Keeps chat answers from repeating themselves.

  * every example gets NEW numbers, designed so it shows what is special about the algorithm
    (a convoy for FCFS, a real preemption for SRTF, ...), and never reuses a process set that this
    student has already seen in this session;
  * each answer uses a teaching angle that was not used in the last few answers;
  * follow-ups like "nope, explain differently" or "another example" are recognised, so the tutor
    knows to change its approach instead of repeating the last answer.
"""
from __future__ import annotations

import random
import re
from collections import deque
from dataclasses import dataclass, field

from core.scheduler_engine import Process, solve

FOLLOW_UP = re.compile(
    r"\b(differently|different\s+(way|example|examples|numbers|approach)|another|again|one\s+more|"
    r"new\s+examples?|more\s+examples?|other\s+examples?|nope|not\s+clear|unclear|"
    r"did\s*n['’]?t\s+(get|understand)|do\s*n['’]?t\s+(get|understand)|confus\w*|simpler|"
    r"re-?explain|explain\s+(it\s+)?(once\s+)?again|still\s+(not|don)|same\s+(thing|example|answer))\b", re.I)
SEPARATE = re.compile(
    r"\b(separate(ly)?|individual(ly)?|one\s+by\s+one|each\s+(one|algorithm)|their\s+own|for\s+each|"
    r"separate\s+examples?)\b", re.I)

# (name, instruction). The model is told to use one of these; recent ones are skipped.
ANGLES = [
    ("timeline", "Walk through the schedule as a timeline: at each time point say what is in the ready queue, "
                 "which process the CPU runs and why."),
    ("ready-queue", "Explain from the ready queue's point of view: who joins, who leaves, and why the scheduler "
                    "picks the process it picks."),
    ("problem-first", "Start from the problem this algorithm is trying to solve, derive its rule from that, then "
                      "apply the rule to the example."),
    ("mistakes", "Teach through the mistakes students make: show the tempting wrong step, why it is wrong, then "
                 "the correct step."),
    ("questions", "Teach it as a short chain of questions a student would ask, each answered right away."),
    ("analogy", "Open with one everyday analogy (a canteen queue, a doctor's clinic, a shared printer), map it "
                "exactly onto the algorithm, then leave the analogy and use the real terms."),
    ("result-first", "Show the final result first, then explain backwards how each number was obtained from "
                     "the Gantt chart."),
]


@dataclass
class Session:
    seen: set = field(default_factory=set)                 # process sets already shown
    angles: deque = field(default_factory=lambda: deque(maxlen=4))
    last_algos: list = field(default_factory=list)
    last_kind: str | None = None
    last_domain: str | None = None                          # cpu, bankers, page, disk, alloc


_SESSIONS: dict[str, Session] = {}


def session(student: str) -> Session:
    key = (student or "guest").strip().lower()
    if key not in _SESSIONS:
        if len(_SESSIONS) > 200:                            # keep memory bounded
            _SESSIONS.pop(next(iter(_SESSIONS)))
        _SESSIONS[key] = Session()
    return _SESSIONS[key]


def procs_key(processes: list[dict]) -> tuple:
    return tuple(sorted((p["arrival"], p["burst"], p.get("priority", 0)) for p in processes))


def pick_angle(sess: Session, rng: random.Random | None = None) -> tuple[str, str]:
    rng = rng or random.Random()
    fresh = [a for a in ANGLES if a[0] not in sess.angles] or ANGLES
    name, text = rng.choice(fresh)
    sess.angles.append(name)
    return name, text


def _as_procs(rows) -> list[Process]:
    return [Process(p["pid"], p["arrival"], p["burst"], p.get("priority", 0)) for p in rows]


def _preempts(res) -> bool:
    pids = [s.pid for s in res.gantt if s.pid != "IDLE"]
    return len(pids) != len(set(pids))


def _order(res) -> list[str]:
    seen = []
    for s in res.gantt:
        if s.pid != "IDLE" and s.pid not in seen:
            seen.append(s.pid)
    return seen


def design(algorithm: str | None, avoid: set, rng: random.Random | None = None,
           quantum: int | None = None) -> tuple[list[dict], int | None]:
    """A new example for `algorithm` (None = a mixed set for comparing algorithms).
    Checked with the engine so it actually shows the algorithm's behaviour."""
    rng = rng or random.Random()
    pr = algorithm is None or algorithm.startswith("PRIORITY")
    last = None
    for _ in range(400):
        n = rng.randint(4, 5)
        if algorithm == "FCFS":                      # one long job early -> convoy, sometimes an idle gap
            arr = sorted(rng.sample(range(0, 7), n))
            arr[0] = 0
            bursts = [rng.randint(1, 4) for _ in range(n)]
            bursts[rng.randint(0, 1)] = rng.randint(8, 12)
            if rng.random() < 0.3:
                arr[-1] = arr[-1] + rng.randint(15, 20)
        elif algorithm in ("SRTF", "PRIORITY_P"):    # a long job first, later arrivals cut in
            arr = [0] + sorted(rng.randint(1, 7) for _ in range(n - 1))
            bursts = [rng.randint(6, 10)] + [rng.randint(1, 5) for _ in range(n - 1)]
        else:
            arr = sorted([0] + [rng.randint(0, 8) for _ in range(n - 1)])
            bursts = [rng.randint(1, 9) for _ in range(n)]
        prios = rng.sample(range(1, 6), n) if pr else [0] * n
        rows = [{"pid": f"P{i + 1}", "arrival": a, "burst": b, "priority": p}
                for i, (a, b, p) in enumerate(zip(arr, bursts, prios))]
        q = None
        if algorithm == "RR":
            q = quantum or rng.randint(2, 4)
            if sum(b > q for b in bursts) < 2:
                continue
        last = (rows, q)
        if procs_key(rows) in avoid:
            continue
        procs = _as_procs(rows)
        if algorithm is None:                        # comparison: the algorithms should really differ
            wts = {round(solve(procs, a, 2 if a == "RR" else None).avg_wt, 2)
                   for a in ("FCFS", "SJF", "SRTF", "PRIORITY_NP", "PRIORITY_P", "RR")}
            if len(wts) < 5:
                continue
        elif algorithm in ("SRTF", "PRIORITY_P"):
            if not _preempts(solve(procs, algorithm)):
                continue
        elif algorithm in ("SJF", "PRIORITY_NP"):
            if _order(solve(procs, algorithm)) == _order(solve(procs, "FCFS")):
                continue
        return rows, q
    return last                                       # practically never reached

"""
Numerical problem types beyond CPU scheduling: recognising them in a question, reading the student's
own numbers, and designing fresh examples that are checked with the solvers.

  domain  algorithms                               solver
  ------  ---------------------------------------  -----------------------------
  bankers BANKERS (safety), REQUEST, DETECT        core.os_solvers.bankers / ...
  page    FIFO, LRU, OPT                           core.os_solvers.page_replacement
  disk    D_FCFS, SSTF, SCAN, C-SCAN, LOOK, C-LOOK core.os_solvers.disk
  alloc   FIRST, BEST, WORST, NEXT                 core.os_solvers.allocate
"""
from __future__ import annotations

import json
import random
import re

from core.llm import LLM, LLMError
from core.os_solvers import KIND_ALGOS, Solved, kind_of, solve_any  # noqa: F401

DOMAINS = ["bankers", "page", "disk", "alloc"]
DOMAIN_NAMES = {"bankers": "Banker's algorithm / deadlock", "page": "page replacement", "disk": "disk scheduling",
                "alloc": "contiguous memory allocation", "cpu": "CPU scheduling"}

# Which kind of numerical a question is about (checked before CPU scheduling)
_DETECT = [
    ("bankers", r"banker|safe\s+(state|sequence)|unsafe\s+state|need\s+matrix|max(imum)?\s+matrix|"
                r"allocation\s+matrix|available\s+(vector|resources?)|resource[- ]request|deadlock\s+(avoid|detect)|"
                r"detect(ion|ing)?\s+(algorithm\s+)?(for\s+|of\s+|the\s+)?deadlock|detection\s+algorithm|"
                r"(is|are)\s+(this|the)\s+(state|system)\s+(in\s+a\s+)?safe|\bavailable\b.{0,60}\ballocation\b|"
                r"\ballocation\b.{0,60}\b(max|request)\b"),
    ("page", r"page\s+replace|page\s+faults?|reference\s+string|\bframes?\b|\blru\b|optimal\s+page|belady|"
             r"page\s+hits?"),
    ("disk", r"disk\s+schedul|cylinders?|\bseek\b|sstf|c[- ]?scan|c[- ]?look|elevator|head\s+(movement|position|"
             r"starts?|is\s+at|at\s+\d)|r/w\s+head|read[/-]write\s+head|track"),
    ("alloc", r"first[- ]fit|best[- ]fit|worst[- ]fit|next[- ]fit|memory\s+(partitions?|holes?|blocks?)|"
              r"contiguous\s+(memory\s+)?allocation|dynamic\s+storage[- ]allocation|fixed\s+partition|variable\s+partition"),
]
_ALGOS = {
    "page": [("FIFO", r"\bfifo\b|first[- ]in"), ("LRU", r"\blru\b|least\s+recently"), ("OPT", r"\bopt\b|optimal")],
    "disk": [("C-SCAN", r"c[- ]?scan|circular\s+scan"), ("C-LOOK", r"c[- ]?look|circular\s+look"),
             ("SCAN", r"\bscan\b|elevator"), ("LOOK", r"\blook\b"), ("SSTF", r"sstf|shortest\s+seek"),
             ("D_FCFS", r"\bfcfs\b|first[- ]come|\bfifo\b")],
    "alloc": [("FIRST", r"first[- ]fit"), ("BEST", r"best[- ]fit"), ("WORST", r"worst[- ]fit"), ("NEXT", r"next[- ]fit")],
    "bankers": [("REQUEST", r"\brequests?\b.{0,25}\bP\s*\d|\bP\s*\d\b.{0,25}\brequests?\b|grant"),
                ("DETECT", r"detect")],
}


def detect_domain(text: str) -> str | None:
    for dom, pat in _DETECT:
        if re.search(pat, text, re.I):
            return dom
    return None


def detect_algos(domain: str, text: str) -> list[str]:
    found, rest = {}, text
    for algo, pat in _ALGOS.get(domain, []):
        m = re.search(pat, rest, re.I)
        if m:
            found.setdefault(algo, m.start())
            rest = re.sub(pat, lambda x: " " * len(x.group(0)), rest, flags=re.I)
    algos = sorted(found, key=found.get)
    if domain == "bankers" and not algos:
        algos = ["BANKERS"]
    return algos


# ------------------------------------------------------------------ the student's own numbers
_INT = r"-?\d+"


def _ints(s: str) -> list[int]:
    return [int(x) for x in re.findall(_INT, s)]


def _parse_page(text: str) -> dict | None:
    t = text.lower()
    fr = re.search(r"(\d+)\s*(page\s+)?frames?|frames?\s*(=|:|of|is|are|size)?\s*(\d+)", t)
    frames = int(fr.group(1) or fr.group(4)) if fr else None
    m = re.search(r"(reference\s+string|references?|string|sequence)\s*(is|:|=)?\s*([\d\s,]+)", t)
    refs = _ints(m.group(3)) if m else []
    if len(refs) < 5:                         # longest run of 5+ numbers anywhere
        runs = re.findall(r"(?:\d+[\s,]+){5,}\d+", t)
        refs = _ints(max(runs, key=len)) if runs else []
    if frames and refs and 1 <= frames <= 8 and 5 <= len(refs) <= 40:
        return {"refs": refs, "frames": frames}
    return None


def _parse_disk(text: str) -> dict | None:
    t = text.lower()
    hm = re.search(r"head[^0-9]{0,40}?(\d+)", t)
    rng = re.search(r"(\d+)\s*(?:to|-|–)\s*(\d+)\s*(cylinders?|tracks?)?", t)
    size = re.search(r"(\d+)\s+(cylinders|tracks)", t)
    qm = re.search(r"(queue|requests?|request\s+queue|sequence|order)\s*(is|:|=|of)?\s*([\d\s,]+)", t)
    reqs = _ints(qm.group(3)) if qm else []
    if len(reqs) < 3:
        runs = re.findall(r"(?:\d+[\s,]+){3,}\d+", t)
        reqs = _ints(max(runs, key=len)) if runs else []
    if not hm or len(reqs) < 3:
        return None
    head = int(hm.group(1))
    reqs = [r for r in reqs if r != head] if reqs.count(head) and reqs[0] == head else reqs
    max_cyl = 199
    if rng and int(rng.group(2)) > max(reqs):
        max_cyl = int(rng.group(2))
    elif size and int(size.group(1)) > max(reqs):
        max_cyl = int(size.group(1)) - 1
    direction = "down" if re.search(r"(towards?|direction\s+of)\s+(smaller|lower|decreasing|0\b|zero|inner|"
                                    r"the\s+start)|moving\s+(down|left)|decreasing", t) else "up"
    if max(reqs + [head]) > max_cyl or len(reqs) > 30:
        return None
    return {"requests": reqs, "head": head, "max_cyl": max_cyl, "direction": direction}


def _parse_alloc(text: str) -> dict | None:
    t = text.lower()
    bm = re.search(r"(holes?|partitions?|memory\s+blocks?|blocks?|free\s+space)", t)
    pm = re.search(r"(process(?:es)?|requests?|jobs?)\b", t[bm.end():] if bm else t)
    if not bm or not pm:
        return None
    ppos = bm.end() + pm.start()
    blocks = [b for b in _ints(t[bm.end():ppos]) if b > 0]
    tail = re.split(r"[?.;\n](?!\d)", t[ppos:], maxsplit=1)[0]
    sizes = [s for s in _ints(re.sub(r"\bp\s*\d+\b", " ", tail)) if s > 0]
    if 2 <= len(blocks) <= 10 and 1 <= len(sizes) <= 10:
        return {"blocks": blocks, "sizes": sizes, "names": [f"P{i + 1}" for i in range(len(sizes))]}
    return None


_VEC = r"[\(\[<]?\s*(\d+(?:\s*[,\s]\s*\d+)+)\s*[\)\]>]?"


def _parse_bankers(text: str) -> dict | None:
    """Matrices written as 'Allocation P0 (0,1,0), P1 (2,0,0) ... Max P0 (7,5,3) ... Available (3,3,2)'."""
    t, req = text, None
    m = (re.search(r"\b(P\s*\d+)\s*(?:'s\s+)?(?:makes\s+a\s+|now\s+)?requests?\s*(?:of|for|is|:|=)?\s*" + _VEC, t, re.I)
         or re.search(r"requests?\s+(?:by|from|of)\s+(P\s*\d+)\s*(?:is|:|=|of|for)?\s*" + _VEC, t, re.I))
    if m:
        req = (m.group(1).upper().replace(" ", ""), _ints(m.group(2)))
        t = t[:m.start()] + " " * (m.end() - m.start()) + t[m.end():]
    keys = list(re.finditer(r"\b(available|allocation|allocated|max(?:imum)?|claim|need|requests?(?:\s+matrix)?)\b", t, re.I))
    found: dict = {}
    for i, k in enumerate(keys):
        seg = t[k.end(): keys[i + 1].start() if i + 1 < len(keys) else len(t)]
        w = k.group(1).lower()
        name = ("available" if w.startswith("avail") else "allocation" if w.startswith("alloc") else
                "max" if w.startswith(("max", "claim")) else "need" if w == "need" else "request_matrix")
        if name == "available":
            v = re.search(_VEC, seg)
            if v and "available" not in found:
                found["available"] = _ints(v.group(1))
            continue
        rows = re.findall(r"\b(P\s*\d+)\s*[:=-]?\s*" + _VEC, seg, re.I)
        if rows:
            found.setdefault(name, {}).update((p.upper().replace(" ", ""), _ints(v)) for p, v in rows)
    alloc = found.get("allocation")
    if not alloc or "available" not in found:
        return None
    procs = list(alloc)
    data = {"processes": procs, "allocation": [alloc[p] for p in procs], "available": found["available"]}
    try:
        if "max" in found:
            data["max"] = [found["max"][p] for p in procs]
        elif "need" in found:
            data["max"] = [[a + n for a, n in zip(alloc[p], found["need"][p])] for p in procs]
        elif "request_matrix" in found:
            data["request_matrix"] = [found["request_matrix"][p] for p in procs]
    except KeyError:
        return None
    if req and "max" in data:
        data["request_pid"], data["request"] = req
    return _valid("bankers", data)


EXTRACT_PROMPT = {
    "bankers": """Read the Banker's algorithm / deadlock problem in the message and return JSON only:
{{"processes": ["P0", "P1", ...], "resources": ["A", "B", "C"],
  "allocation": [[...], ...], "max": [[...], ...] or null, "request_matrix": [[...], ...] or null,
  "available": [...], "request_pid": "P1" or null, "request": [...] or null}}
"max" is the Max / Claim matrix; "request_matrix" is only for deadlock detection problems.
If Need is given instead of Max, set max = allocation + need. Use null when the message has no data.

Message: {question}""",
    "page": """Return JSON only: {{"refs": [list of page numbers in the reference string], "frames": number of frames}}
or {{"refs": null}} if the message has no reference string.

Message: {question}""",
    "disk": """Return JSON only: {{"requests": [cylinder numbers in queue order], "head": starting head position,
"max_cyl": highest cylinder number (199 if the disk has 200 cylinders, or if not stated), "direction": "up" or "down"}}
("up" means towards larger cylinder numbers). Use {{"requests": null}} if the message has no request queue.

Message: {question}""",
    "alloc": """Return JSON only: {{"blocks": [memory hole / partition sizes in order], "sizes": [process sizes in order]}}
Use {{"blocks": null}} if the message has no sizes.

Message: {question}""",
}


def _valid(domain: str, d: dict | None) -> dict | None:
    try:
        if not d:
            return None
        if domain == "page":
            refs, f = [int(x) for x in d["refs"]], int(d["frames"])
            return {"refs": refs, "frames": f} if 1 <= f <= 8 and 3 <= len(refs) <= 40 else None
        if domain == "disk":
            req, head = [int(x) for x in d["requests"]], int(d["head"])
            mx = int(d.get("max_cyl") or 199)
            mx = max(mx, max(req + [head]))
            return {"requests": req, "head": head, "max_cyl": mx,
                    "direction": "down" if str(d.get("direction", "up")).lower().startswith("d") else "up"}
        if domain == "alloc":
            b, s = [int(x) for x in d["blocks"]], [int(x) for x in d["sizes"]]
            return {"blocks": b, "sizes": s, "names": [f"P{i + 1}" for i in range(len(s))]} if b and s else None
        if domain == "bankers":
            procs = [str(p).upper().replace(" ", "") for p in d["processes"]]
            res = [str(r) for r in d.get("resources") or [chr(65 + j) for j in range(len(d["available"]))]]
            alloc = [[int(x) for x in row] for row in d["allocation"]]
            avail = [int(x) for x in d["available"]]
            out = {"processes": procs, "resources": res, "allocation": alloc, "available": avail}
            if d.get("request_matrix"):
                out["request_matrix"] = [[int(x) for x in row] for row in d["request_matrix"]]
            if d.get("max"):
                out["max"] = [[int(x) for x in row] for row in d["max"]]
            if d.get("request") and d.get("request_pid"):
                out["request"] = [int(x) for x in d["request"]]
                out["request_pid"] = str(d["request_pid"]).upper().replace(" ", "")
            n, m = len(procs), len(avail)
            ok = len(alloc) == n and all(len(r) == m for r in alloc) and ("max" in out or "request_matrix" in out)
            return out if ok and n <= 10 else None
    except (KeyError, TypeError, ValueError):
        return None
    return None


def extract(domain: str, question: str, llm: LLM | None = None) -> dict | None:
    """The student's own problem data, or None. Regular expressions first, the LLM only as a fallback."""
    if len(re.findall(r"\d+", question)) < 4:
        return None
    parsed = {"page": _parse_page, "disk": _parse_disk, "alloc": _parse_alloc,
              "bankers": _parse_bankers}.get(domain, lambda q: None)(question)
    if parsed:
        return parsed
    if llm is None:
        return None
    try:
        data = llm.chat_json("You extract data. Reply with JSON only.",
                             EXTRACT_PROMPT[domain].format(question=question), temperature=0.0)
    except LLMError:
        return None
    return _valid(domain, data)


# ------------------------------------------------------------------ fresh examples
def key(inputs: dict) -> str:
    return json.dumps(inputs, sort_keys=True)


def _faults(refs, f, a):
    return solve_any(a, {"refs": refs, "frames": f}).view["faults"]


def design(domain: str, algorithm: str | None, avoid: set, rng: random.Random | None = None) -> dict:
    """A new example that shows what the algorithm is about, never one in `avoid`."""
    rng = rng or random.Random()
    last = None
    for _ in range(300):
        if domain == "page":
            pages, f = rng.randint(5, 7), rng.choice([3, 3, 3, 4])
            refs = [rng.randint(0, pages) for _ in range(rng.randint(12, 16))]
            if any(a == b for a, b in zip(refs, refs[1:])):
                continue
            inp = {"refs": refs, "frames": f}
            fifo, lru, opt = (_faults(refs, f, a) for a in ("FIFO", "LRU", "OPT"))
            if not (opt < lru and opt < fifo and fifo != lru and opt >= f + 2):
                continue
        elif domain == "disk":
            mx = 199
            reqs = rng.sample(range(5, mx - 5), rng.randint(7, 8))
            head = rng.randint(40, 150)
            if head in reqs or sum(r < head for r in reqs) < 2 or sum(r > head for r in reqs) < 2:
                continue
            inp = {"requests": reqs, "head": head, "max_cyl": mx, "direction": rng.choice(["up", "up", "down"])}
        elif domain == "alloc":
            blocks = [rng.randint(2, 14) * 50 for _ in range(5)]
            sizes = [rng.randint(2, 12) * 37 + rng.randint(0, 30) for _ in range(4)]
            inp = {"blocks": blocks, "sizes": sizes, "names": ["P1", "P2", "P3", "P4"]}
            places = {a: tuple(solve_any(a, inp).view["placed"].values()) for a in KIND_ALGOS["alloc"]}
            if len(set(places.values())) < 3:
                continue
            if algorithm and algorithm in ("FIRST", "WORST", "NEXT") and None not in places[algorithm] and rng.random() < 0.4:
                continue                       # often show a process that has to wait
        else:  # bankers
            n, m = 5, 3
            procs, res = [f"P{i}" for i in range(n)], ["A", "B", "C"]
            mx = [[rng.randint(1, 9) for _ in range(m)] for _ in range(n)]
            al = [[rng.randint(0, x) for x in row] for row in mx]
            av = [rng.randint(1, 4) for _ in range(m)]
            inp = {"processes": procs, "resources": res, "allocation": al, "max": mx, "available": av}
            if algorithm == "DETECT":
                rq = [[rng.randint(0, 3) for _ in range(m)] for _ in range(n)]
                inp = {"processes": procs, "resources": res, "allocation": al, "request_matrix": rq,
                       "available": [rng.randint(0, 2) for _ in range(m)]}
                if solve_any("DETECT", inp).view["sequence"] == procs:
                    continue
            else:
                base = solve_any("BANKERS", inp)
                want_safe = rng.random() < 0.8
                if base.view["safe"] != want_safe or base.view["sequence"] == procs:
                    continue
                if algorithm == "REQUEST":
                    if not base.view["safe"]:
                        continue
                    i = rng.randrange(n)
                    need = base.view["need"][i]
                    req = [rng.randint(0, min(nd, a)) for nd, a in zip(need, av)]
                    if sum(req) == 0:
                        continue
                    inp.update(request_pid=procs[i], request=req)
        last = inp
        if key(inp) not in avoid:
            return inp
    return last


def solve(algorithm: str, inputs: dict) -> Solved:
    return solve_any(algorithm, inputs)


def default_algos(domain: str) -> list[str]:
    return {"bankers": ["BANKERS"], "page": ["FIFO", "LRU", "OPT"],
            "disk": ["D_FCFS", "SSTF", "SCAN", "C-SCAN", "LOOK", "C-LOOK"],
            "alloc": ["FIRST", "BEST", "WORST", "NEXT"]}[domain]


def design_belady(avoid: set, rng: random.Random | None = None) -> list[int]:
    """A reference string where FIFO gives more faults with 4 frames than with 3: the classic string with its
    pages relabelled (relabelling keeps the anomaly), so a follow-up still gets new numbers."""
    rng = rng or random.Random()
    for _ in range(50):
        labels = rng.sample(range(0, 10), 5)
        refs = [labels[p - 1] for p in [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]]
        if key({"refs": refs, "frames": 3}) not in avoid and _faults(refs, 4, "FIFO") > _faults(refs, 3, "FIFO"):
            return refs
    return [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]

"""Tutor Module: teaches concepts, answers questions, and builds worked examples for the whole OS course.

CPU scheduling problems are solved by core/scheduler_engine.py; Banker's algorithm, page replacement,
disk scheduling and memory allocation by core/os_solvers.py (through core/problems.py). The model
only explains results that are already exact."""
from __future__ import annotations

import re
from typing import Iterator

import config
from core.topic_map import topic_for
from core import problems, prompts, variety
from core.llm import LLM, LLMError
from core.rag import Retriever, Chunk
from core.scheduler_engine import ALGORITHMS, Process, ScheduleResult, processes_from_dicts, solve
from core.os_solvers import NAMES as TASK_NAMES, SHORT as TASK_SHORT, Solved, solve_any
from core.topic_outlines import OUTLINES

# order matters: more specific patterns first
_ALGO_PATTERNS = [
    ("PRIORITY_NP", r"non[- ]?preemptive\s+priority|priority[^.?!]*non[- ]?preemptive"),
    ("PRIORITY_P", r"preemptive\s+priority|priority[^.?!]*preemptive"),
    ("PRIORITY_NP", r"priority"),
    ("SRTF", r"srtf|srjf|shortest\s+remaining|preemptive\s+sjf"),
    ("SJF", r"\bsjf\b|shortest\s+job"),
    ("RR", r"round\s*robin|\brr\b|time\s+quantum|time\s+slice"),
    ("FCFS", r"fcfs|first[- ]come|\bfifo\b"),
]
_NUMERIC_WORDS = re.compile(
    r"\b(gantt|solve|solving|solution|numericals?|calculate|calculation|compute|draw|construct|worked|"
    r"waiting\s+time|turnaround|completion\s+time|response\s+time|average|throughput|utili[sz]ation|"
    r"step[- ]by[- ]step)\b", re.I)
_EXAMPLE_WORDS = re.compile(r"\b(examples?|show|demonstrate|illustrate|problems?)\b", re.I)
_COMPARE_WORDS = re.compile(r"\b(compare|comparison|vs\.?|versus|difference|differ|better|best|which)\b", re.I)
_ALL_ALGOS = re.compile(r"\b(all|every|each)\s+(the\s+|three\s+|six\s+|four\s+)?(scheduling\s+|replacement\s+|"
                        r"page\s+replacement\s+|disk\s+scheduling\s+|allocation\s+)?(algorithms?|strategies|methods)\b", re.I)
# a numerical question is only treated as CPU scheduling if it is about CPU scheduling
_CPU_CONTEXT = re.compile(r"gantt|burst|arrival|turnaround|waiting\s+time|response\s+time|schedul|quantum|"
                          r"time\s+slice|\bcpu\b|\bAT\b|\bBT\b|completion\s+time|ready\s+queue|convoy|\bstarv|\bag(e)?ing\b", re.I)
_TASK_NUMERIC = re.compile(r"page\s+faults?|hits?|hit\s+ratio|head\s+movement|seek|safe\s+sequence|safe\s+state|"
                           r"(state|system)\s+(in\s+a\s+)?safe|"
                           r"\bneed\b|grant|allocate|placement|place\s+the|fragmentation|deadlocked", re.I)

# Problems built to demonstrate one concept (results verified with the engine)
_FIXED = {
    "convoy": [{"pid": "P1", "arrival": 0, "burst": 20, "priority": 0}, {"pid": "P2", "arrival": 0, "burst": 3, "priority": 0},
               {"pid": "P3", "arrival": 0, "burst": 2, "priority": 0}, {"pid": "P4", "arrival": 0, "burst": 1, "priority": 0}],
    "starvation": [{"pid": "P1", "arrival": 0, "burst": 3, "priority": 5}, {"pid": "P2", "arrival": 1, "burst": 4, "priority": 1},
                   {"pid": "P3", "arrival": 4, "burst": 4, "priority": 2}, {"pid": "P4", "arrival": 8, "burst": 4, "priority": 1},
                   {"pid": "P5", "arrival": 12, "burst": 3, "priority": 2}],
    "mixed": [{"pid": "P1", "arrival": 0, "burst": 7, "priority": 3}, {"pid": "P2", "arrival": 2, "burst": 4, "priority": 1},
              {"pid": "P3", "arrival": 4, "burst": 1, "priority": 4}, {"pid": "P4", "arrival": 5, "burst": 4, "priority": 2}],
    "rr": [{"pid": "P1", "arrival": 0, "burst": 5, "priority": 0}, {"pid": "P2", "arrival": 1, "burst": 4, "priority": 0},
           {"pid": "P3", "arrival": 2, "burst": 2, "priority": 0}, {"pid": "P4", "arrival": 4, "burst": 1, "priority": 0}],
}
_DEMOS = [  # (pattern, focus, runs [(label, algo, quantum)], fixed problem)
    (r"convoy", "the convoy effect: short processes stuck behind one long process in FCFS, and how SJF fixes it",
     [("FCFS", "FCFS", None), ("SJF", "SJF", None)], "convoy"),
    (r"\bstarv|\bag(e)?ing\b|indefinite\s+block", "starvation: the low-priority process P1 keeps getting pushed back; "
     "explain how aging would fix it", [("Preemptive Priority", "PRIORITY_P", None)], "starvation"),
    (r"(effect|impact|size|choos|large|small|differ|chang|vary|affect|big|short|long)\w*.{0,40}(quantum|time\s+slice)|"
     r"(quantum|time\s+slice).{0,40}(effect|impact|size|large|small|affect|differ|big|short|long)",
     "how the size of the time quantum changes Round Robin (response time vs context switches; a very large quantum "
     "becomes FCFS)", [("RR q=1", "RR", 1), ("RR q=3", "RR", 3), ("RR q=10", "RR", 10)], "rr"),
    (r"preemptive\s+(vs\.?|versus|and|or)\s+non[- ]?preemptive|non[- ]?preemptive\s+(vs\.?|versus|and|or)\s+preemptive|"
     r"difference\s+between\s+(non[- ]?)?preemptive", "preemptive vs non-preemptive scheduling: the same rule with "
     "and without preemption", [("SJF (non-preemptive)", "SJF", None), ("SRTF (preemptive)", "SRTF", None)], "mixed"),
]

_DEMO_ALGO = {"convoy": "FCFS", "starvation": "PRIORITY_P", "rr": "RR", "mixed": None}

PLAIN_CONTEXT = ("(Plain AI mode: no course material was retrieved. Answer from your own knowledge of "
                 "Operating Systems, using the conventions in your instructions.)")
BELADY = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]

LABELS = {"FCFS": "FCFS", "SJF": "SJF", "SRTF": "SRTF", "PRIORITY_NP": "Priority (non-preemptive)",
          "PRIORITY_P": "Priority (preemptive)", "RR": "Round Robin"}


def detect_algorithms(text: str) -> list[str]:
    """All algorithms named in the text, in the order they are mentioned, without double counting."""
    found: dict[str, int] = {}
    remaining = text
    for algo, pattern in _ALGO_PATTERNS:
        m = re.search(pattern, remaining, re.I)
        if m:
            found.setdefault(algo, m.start())
            remaining = re.sub(pattern, lambda x: " " * len(x.group(0)), remaining, flags=re.I)
    return sorted(found, key=found.get)


def detect_algorithm(text: str) -> str | None:
    algos = detect_algorithms(text)
    return algos[0] if algos else None


def with_style(user_prompt: str, style: str) -> str:
    """Put the emotion/tone instruction at the end of the prompt, where small models follow it best."""
    return f"{user_prompt}\n\n{style}" if style else user_prompt


def process_table_text(processes: list[dict], with_priority: bool) -> str:
    head = "PID | AT | BT" + (" | Priority" if with_priority else "")
    rows = [
        f"{p['pid']} | {p['arrival']} | {p['burst']}" + (f" | {p['priority']}" if with_priority else "")
        for p in processes
    ]
    return "\n".join([head, *rows])


class Tutor:
    def __init__(self, llm: LLM, retriever: Retriever):
        self.llm = llm
        self.retriever = retriever

    # ------------------------------------------------------------ routing
    def route(self, question: str, history: list[dict] | None = None, sess: variety.Session | None = None) -> dict:
        """Pick the domain first (CPU scheduling or one of the other numerical units), then the answer type.
        Follow-ups that name nothing stay in the domain of the previous question."""
        sess = sess or variety.Session()
        domain = problems.detect_domain(question)
        cpu_named = bool(detect_algorithms(question)) and bool(_CPU_CONTEXT.search(question))
        if (domain is None and not cpu_named and variety.FOLLOW_UP.search(question)
                and sess.last_domain not in (None, "cpu")):
            domain = sess.last_domain
        if domain is None or cpu_named and not problems.detect_algos(domain, question):
            plan = self._route_cpu(question, history, sess)
            other = topic_for(question)
            if (plan["kind"] != "concept" and not plan["algos"] and not _CPU_CONTEXT.search(question)
                    and not plan.get("user_data") and other and config.UNIT_OF.get(other) != "CPU Scheduling"):
                # "explain paging with an example": an example request about another unit is a concept answer
                plan.update(kind="concept", runs=[], note="")
            about_cpu = plan["kind"] != "concept" or bool(_CPU_CONTEXT.search(question)) or bool(plan["algos"])
            plan["domain"] = "cpu" if about_cpu else "general"
            return plan
        return self._route_task(question, domain, sess)

    def _route_task(self, question: str, domain: str, sess: variety.Session) -> dict:
        """Banker's algorithm, page replacement, disk scheduling or memory allocation."""
        followup = bool(variety.FOLLOW_UP.search(question))
        algos = problems.detect_algos(domain, question)
        named = [a for a in algos if a != "BANKERS"]
        inherited = False
        if not named and followup and sess.last_domain == domain and sess.last_algos:
            algos, inherited = list(sess.last_algos), True
        inputs = problems.extract(domain, question, self.llm)
        plan = {"kind": "concept", "domain": domain, "runs": [], "inputs": inputs, "user_data": bool(inputs),
                "focus": "", "note": "", "followup": followup, "algos": algos, "algorithm": algos[0] if algos else None,
                "processes": None, "time_quantum": None, "user_quantum": None}
        if not inputs and len(re.findall(r"\d+", question)) >= 6:
            plan["note"] = "I couldn't read all of your numbers, so here is a similar example instead."
        numeric = bool(inputs) or bool(_NUMERIC_WORDS.search(question) or _EXAMPLE_WORDS.search(question)
                                       or _TASK_NUMERIC.search(question)) or (
            len(named) >= 2 and bool(_COMPARE_WORDS.search(question))) or (
            inherited and sess.last_kind in ("example", "compare", "series"))
        definition = bool(re.search(r"\b(define|definition|meaning|what (is|are|does))\b", question, re.I)) and not (
            inputs or _EXAMPLE_WORDS.search(question) or re.search(r"\b(solve|calculate|compute|find)\b", question, re.I))
        # Belady's anomaly: FIFO with more frames giving more faults
        if domain == "page" and re.search(r"belady", question, re.I) and not inputs:
            refs = BELADY if (not followup and problems.key({"refs": BELADY, "frames": 3}) not in sess.seen) \
                else problems.design_belady(sess.seen)
            plan.update(kind="compare", algos=["FIFO"], focus="Belady's anomaly: FIFO gives MORE page faults with "
                        "more frames on this reference string; explain why, and why LRU and OPT never do this",
                        runs=[("FIFO, 3 frames", "FIFO", {"refs": refs, "frames": 3}),
                              ("FIFO, 4 frames", "FIFO", {"refs": refs, "frames": 4})])
            return plan
        if not numeric or definition:
            return plan
        if domain == "bankers":
            algo = "REQUEST" if (inputs and "request" in inputs) else "DETECT" if (
                inputs and "request_matrix" in inputs) else algos[0]
            plan.update(kind="example", algorithm=algo, algos=[algo], runs=[(TASK_NAMES[algo], algo, inputs)])
            return plan
        every = bool(_ALL_ALGOS.search(question))
        if variety.SEPARATE.search(question) and (len(named) != 1 or every) or (inherited and sess.last_kind == "series"):
            algos = named if len(named) >= 2 and not every else problems.default_algos(domain)
            plan.update(kind="series", algos=algos, runs=[(TASK_NAMES[a], a, inputs) for a in algos])
        elif len(named) >= 2 or every or not named or (named and _COMPARE_WORDS.search(question) and len(named) >= 2):
            algos = named if len(named) >= 2 and not every else problems.default_algos(domain)
            plan.update(kind="compare", algos=algos, runs=[(TASK_SHORT.get(a, a), a, inputs) for a in algos])
            if not named and not every:
                plan["note"] = (plan["note"] + " " if plan["note"] else "") + (
                    "You didn't name an algorithm, so here they all are on the same problem. Name one to see it "
                    "step by step.")
        else:
            plan.update(kind="example", algorithm=named[0], algos=named[:1], runs=[(TASK_NAMES[named[0]], named[0], inputs)])
        return plan

    def _route_cpu(self, question: str, history: list[dict] | None = None, sess: variety.Session | None = None) -> dict:
        """Decide how to teach this question.

        kind = "concept"  -> written explanation (with examples in text)
               "example"  -> one algorithm solved step by step with a Gantt chart
               "compare"  -> the same processes run through several algorithms / quantums
               "series"   -> a separate example for each algorithm, each explained step by step
        Follow-ups ("nope, explain differently", "another example") reuse the earlier topic but get
        new numbers and a new teaching angle.
        """
        sess = sess or variety.Session()
        algos = detect_algorithms(question)
        if _ALL_ALGOS.search(question):
            algos = list(LABELS)
        followup = bool(variety.FOLLOW_UP.search(question))
        inherited, last_kind = False, sess.last_kind
        demo_named = any(re.search(d[0], question, re.I) for d in _DEMOS)
        if not algos and followup and not demo_named:
            if sess.last_algos:
                algos = list(sess.last_algos)
            else:                                   # e.g. after a server restart: read the chat history
                algos = self._algos_from_history(history)
                last_user = next((m.get("content", "") for m in reversed(history or []) if m.get("role") == "user"), "")
                if _EXAMPLE_WORDS.search(last_user) or _NUMERIC_WORDS.search(last_user):
                    last_kind = "example"
            inherited = bool(algos)
        has_data = bool(re.search(r"\bp\s*\d", question, re.I)) and len(re.findall(r"\d+", question)) >= 4
        quantum = None
        m = re.search(r"(?:quantum|time\s+slice|\bq)\s*(?:=|:|of|is)?\s*(\d+)", question, re.I)
        if m:
            quantum = int(m.group(1))
        plan = {"kind": "concept", "runs": [], "processes": None, "user_data": False,
                "focus": "", "note": "", "time_quantum": quantum, "algorithm": algos[0] if algos else None,
                "followup": followup, "algos": algos, "user_quantum": quantum}

        # 1. the student's own process data
        if has_data:
            try:
                data = self.llm.chat_json("You extract data. Reply with JSON only.",
                                          prompts.ROUTER.format(question=question), temperature=0.0)
                procs = self._clean_processes(data.get("processes"))
                if procs:
                    plan["processes"], plan["user_data"] = procs, True
                    if not algos and data.get("algorithm") in ALGORITHMS:
                        algos = [data["algorithm"]]
                    if not quantum and isinstance(data.get("time_quantum"), int) and data["time_quantum"] > 0:
                        quantum = data["time_quantum"]
            except LLMError:
                pass
            if not plan["user_data"]:
                plan["note"] = "I couldn't read your process table, so here is a similar example instead."

        # 2. concept demonstrations (convoy effect, starvation, quantum size, preemption)
        if not plan["user_data"] and len(algos) <= 1 or (plan["user_data"] and not algos):
            for pattern, focus, runs, fixed in _DEMOS:
                if re.search(pattern, question, re.I):
                    procs = plan["processes"] or [dict(p) for p in _FIXED[fixed]]
                    if not plan["user_data"] and (followup or variety.procs_key(procs) in sess.seen):
                        procs, _ = variety.design(_DEMO_ALGO[fixed], sess.seen)   # same idea, new numbers
                    plan.update(kind="compare" if len(runs) > 1 else "example", focus=focus, processes=procs)
                    plan["runs"] = [(label, a, q) for label, a, q in runs]
                    plan["algos"] = list(dict.fromkeys(a for _, a, _ in runs))
                    plan["algorithm"] = runs[0][1]
                    plan["time_quantum"] = runs[0][2]
                    return plan

        # 3a. a separate example for each algorithm
        if len(algos) >= 2 and (variety.SEPARATE.search(question) or (inherited and last_kind == "series")):
            plan.update(kind="series", runs=[(LABELS[a], a, (quantum or None) if a == "RR" else None) for a in algos])
            return plan

        # 3b. comparison of several algorithms (same processes)
        if len(algos) >= 2 or (len(algos) >= 1 and plan["user_data"] and _COMPARE_WORDS.search(question)
                               and len(algos) >= 2):
            q = quantum or 2
            plan.update(kind="compare", runs=[(LABELS[a] + (f" q={q}" if a == "RR" else ""), a,
                                               q if a == "RR" else None) for a in algos])
            if not plan["processes"]:
                plan["processes"], _ = variety.design(None, sess.seen)
            return plan

        # 4. one algorithm, solved step by step
        definition = bool(re.search(r"\b(formulas?|define|definition|meaning|what (is|are|does)|stands? for)\b",
                                    question, re.I)) and not _EXAMPLE_WORDS.search(question) and not re.search(
                                    r"\b(gantt|solve|calculate|compute)\b", question, re.I)
        numeric = (not definition and bool(_NUMERIC_WORDS.search(question))
                   and bool(_CPU_CONTEXT.search(question) or algos)) or plan["user_data"] or (bool(algos) and bool(_EXAMPLE_WORDS.search(question))) or (
            inherited and last_kind in ("example", "compare", "series"))
        if not numeric:
            return plan  # concept answer
        algo = algos[0] if algos else "FCFS"
        if not algos:
            plan["note"] = (plan["note"] + " " if plan["note"] else "") + (
                "You didn't name an algorithm, so this uses FCFS, the simplest one to learn with. "
                "Ask for SJF, SRTF, Priority or Round Robin, or compare several, to see those.")
        q = (quantum or 2) if algo == "RR" else None
        plan.update(kind="example", algorithm=algo, time_quantum=q,
                    runs=[(LABELS[algo], algo, q)])
        return plan

    def _find(self, query: str, plain: bool = False, **kw) -> tuple[list[Chunk], str]:
        """RAG step: embed the query, search FAISS, format the chunks for the prompt.
        Plain AI mode skips it and lets the model answer from what it already knows."""
        if plain:
            return [], PLAIN_CONTEXT
        chunks = self.retriever.retrieve(query, **kw)
        return chunks, Retriever.format_context(chunks)

    @staticmethod
    def _algos_from_history(history: list[dict] | None) -> list[str]:
        """The algorithms the student last asked about, for follow-ups after a server restart."""
        for m in reversed(history or []):
            if m.get("role") == "user":
                text = m.get("content", "")
                if _ALL_ALGOS.search(text):
                    return list(LABELS)
                found = detect_algorithms(text)
                if found:
                    return found
        return []

    @staticmethod
    def _clean_processes(items) -> list[dict] | None:
        if not isinstance(items, list) or not 1 <= len(items) <= 12:
            return None
        clean = []
        for i, p in enumerate(items, 1):
            try:
                at = int(p.get("arrival") or 0)
                bt = int(p["burst"])
                pr = int(p.get("priority") or 0)
            except (KeyError, TypeError, ValueError, AttributeError):
                return None
            if at < 0 or not 1 <= bt <= 200:
                return None
            pid = str(p.get("pid") or f"P{i}").strip().upper().replace(" ", "")
            clean.append({"pid": pid if re.fullmatch(r"P\d+", pid) else f"P{i}",
                          "arrival": at, "burst": bt, "priority": pr})
        if len({p["pid"] for p in clean}) != len(clean):
            for i, p in enumerate(clean, 1):
                p["pid"] = f"P{i}"
        return clean

    @staticmethod
    def build_problem(processes: list[dict], algorithm: str, time_quantum: int | None, topic: str) -> dict:
        problem = {"scenario": "", "processes": processes, "time_quantum": time_quantum,
                   "algorithm": algorithm, "topic": topic, "difficulty": "medium"}
        problem["solution"] = solve(processes_from_dicts(processes), algorithm, time_quantum)
        return problem

    # ------------------------------------------------------------ teaching
    def stream_lesson(self, topic: str, difficulty: str, weak_concepts: list[str] | None = None,
                      style: str = "", sess: variety.Session | None = None) -> tuple[Iterator[str], list[Chunk]]:
        """A lesson built from the topic's outline, so it covers the syllabus points and stays on the topic.
        Numerical topics get a worked example solved by the engine, so its numbers are exact."""
        outline = OUTLINES.get(topic)
        if outline is None:                                 # unknown topic: fall back to a focused answer
            return self.stream_answer(f"Teach me {topic}.", None, style)
        level = difficulty if difficulty in prompts.LESSON_LEVEL else "medium"
        query = f"{topic} {outline['query']} " + " ".join(weak_concepts or [])
        chunks = self.retriever.retrieve(query, k=5 if level == "hard" else 4,
                                         max_universal=3 if level == "hard" else 2)
        example = ""
        if isinstance(outline["example"], dict):               # Banker's, page replacement, disk, memory
            algo, inputs = outline["example"]["algo"], outline["example"]["inputs"]
            domain = problems.kind_of(algo)
            if sess is not None and problems.key(inputs) in sess.seen:      # lesson repeated: new numbers
                inputs = problems.design(domain, algo, sess.seen)
            if sess is not None:
                sess.seen.add(problems.key(inputs))
            res = solve_any(algo, inputs)
            example = (f"EXACT WORKED EXAMPLE ({res.name}), computed by our solver - use these numbers exactly:\n"
                       f"{res.problem_text()}\nTrace:\n{res.steps_text()}\nResult:\n{res.summary_text()}\n")
        elif outline["example"]:
            algo, procs, q = outline["example"]
            rows = [{"pid": p[0], "arrival": p[1], "burst": p[2], "priority": p[3]} for p in procs]
            if sess is not None and variety.procs_key(rows) in sess.seen:   # lesson repeated: new numbers
                rows, q = variety.design(algo, sess.seen, quantum=q)
                procs = [(r["pid"], r["arrival"], r["burst"], r["priority"]) for r in rows]
            if sess is not None:
                sess.seen.add(variety.procs_key(rows))
            res = solve([Process(*p) for p in procs], algo, q)
            with_pr = algo.startswith("PRIORITY")
            table = process_table_text([{"pid": p[0], "arrival": p[1], "burst": p[2], "priority": p[3]}
                                        for p in procs], with_pr)
            example = (f"EXACT WORKED EXAMPLE ({ALGORITHMS[algo]}" + (f", time quantum {q}" if q else "")
                       + f"), computed by our scheduler - use these numbers exactly:\n{table}\n"
                       f"Decision trace:\n{res.steps_text()}\nGantt chart: {res.gantt_text()}\n{res.table_text()}\n")
        focus = prompts.RELEARN_FOCUS.format(weak=", ".join(weak_concepts)) if weak_concepts else ""
        user = prompts.LESSON_COMMON.format(
            context=Retriever.format_context(chunks), topic=topic,
            cover="\n".join(f"- {x}" for x in outline["cover"]),
            facts="\n".join(f"- {x}" for x in outline["facts"]),
            example=example, focus=(focus + "\n") if focus else "", not_here=outline["not_here"],
        ) + "\n" + prompts.LESSON_LEVEL[level].replace(
            "{advanced}", "\n".join(f"- {x}" for x in outline["advanced"]))
        return self.llm.stream(prompts.TUTOR_SYSTEM, with_style(user, style), temperature=0.35), chunks

    def stream_answer(self, question: str, history: list[dict] | None = None, style: str = "",
                      note: str = "", temperature: float | None = None,
                      plain: bool = False) -> tuple[Iterator[str], list[Chunk]]:
        recent = [m for m in (history or []) if m.get("content")][-4:]
        convo = ""
        if recent:
            convo = "EARLIER IN THIS CONVERSATION:\n" + "\n".join(
                f"{m['role'].upper()}: {m['content'][:600]}" for m in recent) + "\n\n"
        # Use a wider evidence window for open-ended chat: lecture notes are syllabus-specific,
        # while the indexed universal textbooks/reference docs fill detail gaps. Plain mode remains explicit.
        if plain:
            chunks, context = self._find(question, plain=True)
        else:
            chunks = self.retriever.retrieve(question, k=6, max_universal=4)
            context = Retriever.format_context(chunks)
        user = prompts.ANSWER_QUESTION.format(context=context,
                                              history=convo, question=question, variety=note)
        return self.llm.stream(prompts.TUTOR_SYSTEM, with_style(user, style),
                               temperature=0.5 if temperature is None else temperature), chunks

    def stream_social(self, message: str, reading: dict, history: list[dict] | None = None,
                      style: str = "") -> tuple[Iterator[str], list[Chunk]]:
        """Reply to a message that is mainly a feeling, greeting or thanks (no retrieval needed)."""
        recent = [m for m in (history or []) if m.get("content")][-4:]
        convo = "\n".join(f"{m['role'].upper()}: {m['content'][:400]}" for m in recent)
        user = prompts.SOCIAL.format(history=convo or "(start of conversation)", message=message,
                                     mood=reading.get("label", "neutral"), cues=", ".join(reading.get("cues", [])) or "none")
        return self.llm.stream(prompts.TUTOR_SYSTEM, with_style(user, style), temperature=0.6), []

    @staticmethod
    def context_switches(result: ScheduleResult) -> int:
        pids = [s.pid for s in result.gantt if s.pid != "IDLE"]
        return sum(1 for a, b in zip(pids, pids[1:]) if a != b)

    def build_comparison(self, processes: list[dict], runs: list[tuple]) -> dict:
        results = []
        for label, algo, q in runs:
            res = solve(processes_from_dicts(processes), algo, q)
            results.append({"label": label, "algorithm": algo, "time_quantum": q, "solution": res,
                            "switches": self.context_switches(res)})
        return {"processes": processes, "results": results,
                "with_priority": any(r["algorithm"].startswith("PRIORITY") for r in results)}

    def stream_comparison(self, comparison: dict, request: str, focus: str = "", style: str = "",
                          note: str = "", temperature: float = 0.4,
                          plain: bool = False) -> tuple[Iterator[str], list[Chunk]]:
        algos = " ".join(ALGORITHMS[r["algorithm"]] for r in comparison["results"])
        chunks, context = self._find(f"compare {algos} {focus}", plain)
        runs = "\n\n".join(
            f"--- {r['label']} ---\nGantt chart: {r['solution'].gantt_text()}\n{r['solution'].table_text()}\n"
            f"Context switches: {r['switches']}" for r in comparison["results"])
        user = prompts.COMPARE.format(
            context=context, request=request,
            focus=f"Focus on: {focus}" if focus else "",
            processes=process_table_text(comparison["processes"], comparison["with_priority"]),
            runs=runs, variety=note)
        return self.llm.stream(prompts.TUTOR_SYSTEM, with_style(user, style), temperature=temperature), chunks

    def stream_worked_example(self, problem: dict, solution: ScheduleResult, difficulty: str,
                              request: str = "Show me a worked example.",
                              focus: str = "", style: str = "", note: str = "",
                              temperature: float = 0.4, plain: bool = False) -> tuple[Iterator[str], list[Chunk]]:
        algo = problem["algorithm"]
        chunks, context = self._find(f"{ALGORITHMS[algo]} Gantt chart how to construct waiting time", plain)
        user = prompts.WORKED_EXAMPLE.format(
            context=context,
            request=request,
            focus=f"Focus your teaching on: {focus}" if focus else "",
            algorithm_name=ALGORITHMS[algo],
            level=difficulty,
            processes=process_table_text(problem["processes"], algo.startswith("PRIORITY")),
            quantum=f"Time quantum = {problem['time_quantum']}" if algo == "RR" else "",
            steps=solution.steps_text(),
            gantt=solution.gantt_text(),
            table=solution.table_text(),
            variety=note,
        )
        return self.llm.stream(prompts.TUTOR_SYSTEM, with_style(user, style), temperature=temperature), chunks

    def stream_series_step(self, problem: dict, index: int, total: int, request: str, style: str = "",
                           note: str = "", temperature: float = 0.45,
                           plain: bool = False) -> tuple[Iterator[str], list[Chunk]]:
        """One part of a 'separate example for each algorithm' answer (kept short so the whole answer is quick)."""
        algo, sol = problem["algorithm"], problem["solution"]
        chunks, context = self._find(f"{ALGORITHMS[algo]} rule example", plain, k=2)
        user = prompts.SERIES_STEP.format(
            context=context, request=request, index=index, total=total,
            algorithm_name=ALGORITHMS[algo], shows=prompts.SERIES_SHOWS[algo], variety=note,
            processes=process_table_text(problem["processes"], algo.startswith("PRIORITY")),
            quantum=f"Time quantum = {problem['time_quantum']}" if algo == "RR" else "",
            steps=sol.steps_text(), gantt=sol.gantt_text(), table=sol.table_text())
        return self.llm.stream(prompts.TUTOR_SYSTEM, with_style(user, style), temperature=temperature), chunks

    # ------------------------------------------------------------ other numericals
    @staticmethod
    def solve_task(algo: str, inputs: dict) -> Solved:
        return solve_any(algo, inputs)

    def stream_task(self, solved: Solved, request: str, level: str = "standard", focus: str = "", style: str = "",
                    note: str = "", temperature: float = 0.4, plain: bool = False) -> tuple[Iterator[str], list[Chunk]]:
        chunks, context = self._find(f"{solved.name} how to solve step by step", plain)
        user = prompts.WORKED_TASK.format(
            context=context, request=request, focus=f"Focus your teaching on: {focus}" if focus else "",
            variety=note, algorithm_name=solved.name, level=level, problem=solved.problem_text(),
            steps=solved.steps_text(), summary=solved.summary_text(), sections=prompts.TASK_SECTIONS[solved.kind])
        return self.llm.stream(prompts.TUTOR_SYSTEM, with_style(user, style), temperature=temperature), chunks

    def stream_task_compare(self, solved: list[Solved], labels: list[str], request: str, focus: str = "",
                            style: str = "", note: str = "", temperature: float = 0.4,
                            plain: bool = False) -> tuple[Iterator[str], list[Chunk]]:
        names = " ".join(s.name for s in solved)
        chunks, context = self._find(f"compare {names} {focus}", plain)
        runs = "\n\n".join(f"--- {lab} ---\n" + (f"(problem: {s.problem_text()})\n" if len({x.problem_text() for x in solved}) > 1 else "")
                            + f"Trace:\n{s.steps_text()}\nResult:\n{s.summary_text()}" for lab, s in zip(labels, solved))
        problem = solved[0].problem_text() if len({x.problem_text() for x in solved}) == 1 else "(see each run)"
        user = prompts.COMPARE_TASK.format(context=context, request=request + (f"\nFocus on: {focus}" if focus else ""),
                                           problem=problem, runs=runs, variety=note)
        return self.llm.stream(prompts.TUTOR_SYSTEM, with_style(user, style), temperature=temperature), chunks

    def stream_task_step(self, solved: Solved, index: int, total: int, request: str, style: str = "", note: str = "",
                         temperature: float = 0.45, plain: bool = False) -> tuple[Iterator[str], list[Chunk]]:
        chunks, context = self._find(f"{solved.name} rule example", plain, k=2)
        user = prompts.SERIES_TASK.format(context=context, request=request, index=index, total=total,
                                          algorithm_name=solved.name, variety=note, problem=solved.problem_text(),
                                          steps=solved.steps_text(), summary=solved.summary_text())
        return self.llm.stream(prompts.TUTOR_SYSTEM, with_style(user, style), temperature=temperature), chunks

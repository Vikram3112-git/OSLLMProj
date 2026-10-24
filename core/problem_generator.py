"""Problem Generator: MCQs, numerical problems and viva questions."""
from __future__ import annotations

import random

import config
from core import prompts
from core.llm import LLM, LLMError
from core.rag import Retriever
from core import problems
from core.os_solvers import kind_of
from core.scheduler_engine import ALGORITHMS, processes_from_dicts, solve

LIMITS = {  # (n_min, n_max, max_arrival, max_burst) used to validate LLM output
    "easy": (3, 4, 3, 8),
    "medium": (4, 5, 8, 10),
    "hard": (5, 6, 15, 12),
}


def _focus(weak: list[str] | None) -> str:
    return f"Target this weak area of the student if relevant: {', '.join(weak)}." if weak else ""


class ProblemGenerator:
    def __init__(self, llm: LLM, retriever: Retriever):
        self.llm = llm
        self.retriever = retriever

    # ---------------------------------------------------------------- MCQ
    def mcq(self, topic: str, difficulty: str, weak: list[str] | None = None) -> dict:
        chunks = self.retriever.retrieve(f"{topic} operating systems " + " ".join(weak or []))
        user = prompts.MCQ.format(context=Retriever.format_context(chunks), topic=topic,
                                  difficulty=difficulty, focus=_focus(weak))
        for _ in range(3):
            q = self.llm.chat_json(prompts.GEN_SYSTEM, user, temperature=0.7)
            opts = q.get("options")
            if (isinstance(opts, list) and len(opts) == 4 and q.get("question")
                    and isinstance(q.get("answer_index"), int) and 0 <= q["answer_index"] <= 3):
                q.setdefault("hint", "Re-read the definition of the key term in the question.")
                q.setdefault("explanation", "")
                q.setdefault("concept", topic)
                q["sources"] = chunks
                return q
        raise LLMError("Could not generate a valid MCQ. Try again.")

    # ----------------------------------------------------------- numerical
    def numerical(self, topic: str, difficulty: str, algorithm: str | None = None) -> dict:
        algorithm = algorithm or random.choice(config.NUMERICAL_TOPICS[topic])
        if algorithm not in config.CPU_ALGOS:              # Banker's, page replacement, disk, memory
            return self.task(topic, difficulty, algorithm)
        is_rr = algorithm == "RR"
        is_pr = algorithm.startswith("PRIORITY")
        user = prompts.NUMERICAL.format(
            difficulty=difficulty,
            algorithm_name=ALGORITHMS[algorithm],
            constraints=prompts.NUMERICAL_CONSTRAINTS[difficulty],
            priority_rule=("Give every process a priority from 1 to 5 (1 = highest)." if is_pr
                           else "Set priority to 0 for every process."),
            quantum_field="an integer from 2 to 4" if is_rr else "null",
        )
        problem = None
        try:
            for _ in range(2):
                data = self.llm.chat_json(prompts.GEN_SYSTEM, user, temperature=0.8)
                problem = self._validate(data, difficulty, is_rr, is_pr)
                if problem:
                    break
        except LLMError:
            problem = None
        if problem is None:  # LLM gave unusable numbers -> safe random fallback
            problem = self._random_problem(difficulty, is_rr, is_pr)
        problem["algorithm"] = algorithm
        problem["topic"] = topic
        problem["difficulty"] = difficulty
        problem["solution"] = solve(processes_from_dicts(problem["processes"]), algorithm,
                                    problem.get("time_quantum"))
        return problem

    def _validate(self, data: dict, difficulty: str, is_rr: bool, is_pr: bool) -> dict | None:
        n_min, n_max, max_at, max_bt = LIMITS[difficulty]
        procs = data.get("processes")
        if not isinstance(procs, list) or not n_min <= len(procs) <= n_max + 1:
            return None
        clean = []
        for i, p in enumerate(procs, 1):
            try:
                at, bt = int(p["arrival"]), int(p["burst"])
                pr = int(p.get("priority") or 0)
            except (KeyError, TypeError, ValueError):
                return None
            if not (0 <= at <= max_at + 2 and 1 <= bt <= max_bt + 2):
                return None
            if is_pr and not 1 <= pr <= 9:
                return None
            clean.append({"pid": f"P{i}", "arrival": at, "burst": bt, "priority": pr if is_pr else 0})
        tq = None
        if is_rr:
            try:
                tq = int(data.get("time_quantum"))
            except (TypeError, ValueError):
                return None
            if not 1 <= tq <= 6:
                return None
        return {"scenario": str(data.get("scenario", "")).strip(), "processes": clean, "time_quantum": tq}

    @staticmethod
    def _random_problem(difficulty: str, is_rr: bool, is_pr: bool) -> dict:
        n_min, n_max, max_at, max_bt = LIMITS[difficulty]
        n = random.randint(n_min, n_max)
        arrivals = sorted([0] + [random.randint(0, max_at) for _ in range(n - 1)])
        procs = [{"pid": f"P{i + 1}", "arrival": a, "burst": random.randint(1, max_bt),
                  "priority": random.randint(1, 5) if is_pr else 0} for i, a in enumerate(arrivals)]
        return {"scenario": "A CPU receives the following processes.", "processes": procs,
                "time_quantum": random.randint(2, 4) if is_rr else None}

    @staticmethod
    def task(topic: str, difficulty: str, algorithm: str, avoid: set | None = None) -> dict:
        """A numerical for the non-scheduling units, designed and solved exactly (no LLM needed)."""
        domain = kind_of(algorithm)
        inputs = problems.design(domain, algorithm, avoid or set())
        solved = problems.solve(algorithm, inputs)
        return {"domain": domain, "algorithm": algorithm, "inputs": inputs, "solved": solved, "topic": topic,
                "difficulty": difficulty, "task": True}

    # ----------------------------------------------------------------- viva
    def viva(self, topic: str, difficulty: str, weak: list[str] | None = None) -> dict:
        chunks = self.retriever.retrieve(f"{topic} operating systems viva " + " ".join(weak or []))
        user = prompts.VIVA.format(context=Retriever.format_context(chunks), topic=topic,
                                   difficulty=difficulty, focus=_focus(weak))
        for _ in range(3):
            q = self.llm.chat_json(prompts.GEN_SYSTEM, user, temperature=0.7)
            if q.get("question") and isinstance(q.get("key_points"), list) and q["key_points"]:
                hints = q.get("hints") if isinstance(q.get("hints"), list) else []
                q["hints"] = [str(h) for h in hints][:2] or ["Start from the definition of the key term in the question."]
                q.setdefault("model_answer", "")
                q["sources"] = chunks
                return q
        raise LLMError("Could not generate a valid viva question. Try again.")

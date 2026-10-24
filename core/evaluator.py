"""Evaluator: grades answers, identifies mistakes and gives corrective feedback."""
from __future__ import annotations

import re

import config
from core import prompts
from core.llm import LLM, LLMError
from core.rag import Retriever
from core.scheduler_engine import ALGORITHMS
from core.tutor import process_table_text


def apply_hint_penalty(score: float, hints_used: int) -> float:
    return max(0.0, score * (1 - config.HINT_PENALTY * hints_used))


def parse_gantt_order(text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z]+\d*", text or "")
    out = []
    for tok in tokens:
        tok = tok.upper()
        if tok in {"IDLE", "I"}:
            continue
        if re.fullmatch(r"P\d+", tok):
            if not out or out[-1] != tok:
                out.append(tok)
    return out


def _num(v) -> float | None:
    try:
        if v is None or v == "":
            return None
        f = float(v)
        return None if f != f else f  # NaN -> None
    except (TypeError, ValueError):
        return None


class Evaluator:
    def __init__(self, llm: LLM, retriever: Retriever):
        self.llm = llm
        self.retriever = retriever

    # ---------------------------------------------------------------- MCQ
    def mcq(self, item: dict, chosen: int, hints_used: int) -> dict:
        correct = chosen == item["answer_index"]
        result = {
            "correct": correct,
            "score": apply_hint_penalty(1.0 if correct else 0.0, hints_used),
            "mistakes": [] if correct else [item.get("concept", "concept")],
            "feedback": item.get("explanation", ""),
        }
        if not correct:
            # MCQ grading must be immediate and deterministic. Do not call the local LLM
            # just to explain a wrong choice: on slower computers that request can leave
            # the UI stuck on “Checking…”. Use the verified item explanation instead.
            correct_letter = chr(65 + item["answer_index"])
            chosen_letter = chr(65 + chosen)
            base_explanation = (item.get("explanation") or "").strip()
            result["feedback"] = (
                f"Your choice: {chosen_letter}) {item['options'][chosen]}. "
                f"Correct answer: {correct_letter}) {item['options'][item['answer_index']]}. "
                + (base_explanation or "Review the definition and compare it with the options.")
            )
        return result

    # ----------------------------------------------------------- numerical
    def numerical(self, problem: dict, student: dict, hints_used: int) -> dict:
        """student = {"gantt": str, "rows": {pid: {"CT","TAT","WT"}}, "avg_tat", "avg_wt"}"""
        sol = problem["solution"]
        errors: list[str] = []
        misconceptions: set[str] = set()
        cell_ok: dict[str, dict[str, bool]] = {}
        points, total = 0, 0

        # 1. Gantt chart order
        total += 2
        want = [p for p in sol.order if p != "IDLE"]
        got = parse_gantt_order(student.get("gantt", ""))
        gantt_ok = got == want
        if gantt_ok:
            points += 2
        else:
            errors.append(f"Gantt order given: {' > '.join(got) or '(blank)'}; correct: {' > '.join(want)}")
            misconceptions.add(self._gantt_misconception(problem["algorithm"], got, want))

        # 2. per-process values
        for pid, truth in sol.table.items():
            row = student.get("rows", {}).get(pid, {})
            ct, tat, wt = _num(row.get("CT")), _num(row.get("TAT")), _num(row.get("WT"))
            ok = {
                "CT": ct == truth["completion"],
                "TAT": tat == truth["turnaround"],
                "WT": wt == truth["waiting"],
            }
            cell_ok[pid] = ok
            total += 3
            points += sum(ok.values())
            at, bt = truth["arrival"], truth["burst"]
            missing = [k for k, v in (("CT", ct), ("TAT", tat), ("WT", wt)) if v is None]
            if missing:
                errors.append(f"{pid}: {', '.join(missing)} left blank")
            if not ok["CT"] and ct is not None:
                errors.append(f"{pid}: CT {ct:g} should be {truth['completion']}")
                if gantt_ok:
                    misconceptions.add("reading completion time from the Gantt chart")
            if not ok["TAT"] and tat is not None:
                errors.append(f"{pid}: TAT {tat:g} should be {truth['turnaround']}")
                if ct is not None and tat == ct and at != 0:
                    misconceptions.add("TAT = CT - AT (arrival time not subtracted)")
                elif ct is not None and tat == ct - at:
                    pass  # consistent with their own CT: error carried forward
                else:
                    misconceptions.add("turnaround time formula")
            if not ok["WT"] and wt is not None:
                errors.append(f"{pid}: WT {wt:g} should be {truth['waiting']}")
                start = truth["response"] + at
                if ct is not None and wt == ct - bt and at != 0:
                    misconceptions.add("WT = TAT - BT (used CT - BT, forgot arrival)")
                elif problem["algorithm"] in ("SRTF", "PRIORITY_P", "RR") and wt == start - at and start - at != truth["waiting"]:
                    misconceptions.add("waiting time in preemptive scheduling (confused with response time)")
                elif tat is not None and wt == tat - bt:
                    pass  # consistent with their own TAT
                else:
                    misconceptions.add("waiting time formula")

        # 3. averages
        for key, truth, label in (("avg_tat", sol.avg_tat, "Average TAT"), ("avg_wt", sol.avg_wt, "Average WT")):
            total += 1
            v = _num(student.get(key))
            if v is not None and abs(v - truth) <= 0.01 + 1e-9:
                points += 1
            else:
                errors.append(f"{label} left blank" if v is None else f"{label} {v:g} should be {truth:.2f}")
                if all(all(c.values()) for c in cell_ok.values()):
                    misconceptions.add("averaging the metrics")

        raw = points / total
        misconceptions.discard("")
        result = {
            "score": apply_hint_penalty(raw, hints_used),
            "raw_score": raw,
            "gantt_ok": gantt_ok,
            "cells": cell_ok,
            "errors": errors,
            "mistakes": sorted(misconceptions),
            "feedback": "All correct. Well done!" if not errors else "",
        }
        if errors:
            result["feedback"] = self._numerical_feedback(problem, errors, misconceptions)
        return result

    @staticmethod
    def _gantt_misconception(algo: str, got: list[str], want: list[str]) -> str:
        if not got:
            return "constructing the Gantt chart"
        if algo in ("SRTF", "PRIORITY_P") and len(got) < len(want):
            return "preemption (when a new arrival should interrupt the running process)"
        if algo == "RR":
            return "Round Robin ready-queue order and time quantum"
        if algo in ("SJF", "PRIORITY_NP"):
            return "choosing only among processes that have already arrived"
        return f"{ALGORITHMS[algo]} selection order"

    def _numerical_feedback(self, problem: dict, errors: list[str], misconceptions: set[str]) -> str:
        sol = problem["solution"]
        algo = problem["algorithm"]
        chunks = self.retriever.retrieve(f"{ALGORITHMS[algo]} " + " ".join(misconceptions))
        user = prompts.NUMERICAL_FEEDBACK.format(
            context=Retriever.format_context(chunks),
            algorithm_name=ALGORITHMS[algo],
            processes=process_table_text(problem["processes"], algo.startswith("PRIORITY")),
            quantum=f"Time quantum = {problem['time_quantum']}" if algo == "RR" else "",
            gantt=sol.gantt_text(), table=sol.table_text(),
            errors="\n".join(f"- {e}" for e in errors[:15]),
            misconceptions=", ".join(sorted(misconceptions)) or "none identified",
        )
        try:
            return self.llm.chat(prompts.EVAL_SYSTEM, user, temperature=0.3)
        except LLMError:
            return "Check the highlighted cells against the correct table below."

    def numerical_hint(self, problem: dict, level: int) -> str:
        sol = problem["solution"]
        algo = problem["algorithm"]
        if level >= 3:
            return "Gantt chart: " + sol.gantt_text()
        user = prompts.NUMERICAL_HINT.format(
            algorithm_name=ALGORITHMS[algo],
            processes=process_table_text(problem["processes"], algo.startswith("PRIORITY")),
            quantum=f"Time quantum = {problem['time_quantum']}" if algo == "RR" else "",
            gantt=sol.gantt_text(), level=level,
        )
        return self.llm.chat(prompts.TUTOR_SYSTEM, user, temperature=0.3)

    # ----------------------------------------------------------------- viva
    def viva(self, item: dict, answer: str, hints_used: int) -> dict:
        user = prompts.VIVA_EVAL.format(
            context=Retriever.format_context(item.get("sources", [])),
            question=item["question"], key_points="; ".join(item["key_points"]),
            model_answer=item.get("model_answer", ""), answer=answer.strip() or "(no answer)",
        )
        data = self.llm.chat_json(prompts.EVAL_SYSTEM, user, temperature=0.2)
        try:
            raw = max(0.0, min(10.0, float(data.get("score", 0)))) / 10
        except (TypeError, ValueError):
            raw = 0.0
        if not answer.strip():
            raw = 0.0
        missing = [str(m) for m in data.get("missing_points", []) or []]
        wrong = [str(m) for m in data.get("misconceptions", []) or []]
        return {
            "score": apply_hint_penalty(raw, hints_used),
            "raw_score": raw,
            "covered": [str(c) for c in data.get("covered_points", []) or []],
            "missing": missing,
            "mistakes": (wrong + missing)[:4],
            "feedback": str(data.get("feedback", "")),
        }

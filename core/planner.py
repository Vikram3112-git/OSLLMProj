"""Learning Planner: chooses the next learning activity from student performance."""
from __future__ import annotations

from dataclasses import dataclass

import config
from core.profile_db import ProfileDB

ACTIVITY_LABELS = {
    "lesson": "Concept lesson",
    "relearn": "Re-learn weak concepts",
    "worked_example": "Worked example",
    "mcq": "MCQ",
    "numerical": "Numerical",
    "viva": "Viva question",
}


@dataclass
class PlannedActivity:
    activity: str
    topic: str
    difficulty: str
    reason: str
    weak_concepts: list[str]


def practice_types(topic: str) -> list[str]:
    return ["mcq", "numerical", "viva"] if topic in config.NUMERICAL_TOPICS else ["mcq", "viva"]


def difficulty_for(mastery: float) -> str:
    if mastery < 0.4:
        return "easy"
    if mastery < 0.75:
        return "medium"
    return "hard"


def is_mastered(state: dict) -> bool:
    return state["mastery"] >= config.MASTERED_AT and state["attempts"] >= config.MIN_ATTEMPTS_TO_MASTER


class LearningPlanner:
    def __init__(self, db: ProfileDB):
        self.db = db

    def _pick_practice(self, student_id: int, topic: str, state: dict) -> str:
        types = practice_types(topic)
        scores = self.db.activity_scores(student_id, topic)
        untried = [t for t in types if t not in scores]
        if untried:
            return untried[0]
        # practise the weakest activity type, but don't repeat the same one forever
        ranked = sorted(types, key=lambda t: scores[t])
        if ranked[0] == state.get("last_activity") and len(ranked) > 1 and scores[ranked[1]] < 0.9:
            return ranked[1]
        return ranked[0]

    def next_activity(self, student_id: int) -> PlannedActivity:
        states = self.db.topic_states(student_id)

        for topic in config.TOPICS:
            st = states[topic]
            if is_mastered(st):
                continue
            diff = difficulty_for(st["mastery"])
            weak = self.db.weak_concepts(student_id, topic)

            if st["lessons_seen"] == 0:
                return PlannedActivity("lesson", topic, diff,
                                       f"You haven't studied {topic} yet, so start with the concept.", [])
            if topic in config.NUMERICAL_TOPICS and st["examples_seen"] == 0:
                return PlannedActivity("worked_example", topic, diff,
                                       f"See a solved {topic} problem before practising on your own.", [])
            if (st["attempts_since_lesson"] >= config.RELEARN_AFTER_ATTEMPTS
                    and st["mastery"] < config.RELEARN_BELOW):
                return PlannedActivity("relearn", topic, "easy",
                                       f"Your {topic} score is {st['mastery']:.0%}. Let's revisit the parts "
                                       "you keep getting wrong.", weak)
            activity = self._pick_practice(student_id, topic, st)
            reason = (f"{topic} mastery is {st['mastery']:.0%} "
                      f"(need {config.MASTERED_AT:.0%} over {config.MIN_ATTEMPTS_TO_MASTER}+ attempts). "
                      f"Practising at {diff} level.")
            return PlannedActivity(activity, topic, diff, reason, weak)

        # everything mastered: revise the weakest topic at hard level
        topic = min(config.TOPICS, key=lambda t: states[t]["mastery"])
        return PlannedActivity(self._pick_practice(student_id, topic, states[topic]), topic, "hard",
                               "All topics mastered. Revising your weakest one at hard level.",
                               self.db.weak_concepts(student_id, topic))

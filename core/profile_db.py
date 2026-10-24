"""Student Profile: SQLite storage of progress and topic-wise performance."""
from __future__ import annotations

import json
import sqlite3
from collections import Counter
from datetime import datetime

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS topic_state (
    student_id INTEGER NOT NULL,
    topic TEXT NOT NULL,
    mastery REAL NOT NULL DEFAULT 0,
    attempts INTEGER NOT NULL DEFAULT 0,
    lessons_seen INTEGER NOT NULL DEFAULT 0,
    examples_seen INTEGER NOT NULL DEFAULT 0,
    attempts_since_lesson INTEGER NOT NULL DEFAULT 0,
    last_activity TEXT,
    updated_at TEXT,
    PRIMARY KEY (student_id, topic)
);
CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    topic TEXT NOT NULL,
    activity TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    score REAL NOT NULL,
    hints_used INTEGER NOT NULL DEFAULT 0,
    mistakes TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class ProfileDB:
    def __init__(self, path=config.DB_PATH):
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # --------------------------------------------------------------- students
    def get_or_create_student(self, name: str) -> int:
        name = name.strip()
        row = self.conn.execute("SELECT id FROM students WHERE name = ?", (name,)).fetchone()
        if row:
            return row["id"]
        cur = self.conn.execute("INSERT INTO students (name, created_at) VALUES (?, ?)", (name, _now()))
        sid = cur.lastrowid
        self.conn.executemany(
            "INSERT OR IGNORE INTO topic_state (student_id, topic, updated_at) VALUES (?, ?, ?)",
            [(sid, t, _now()) for t in config.TOPICS],
        )
        self.conn.commit()
        return sid

    # ------------------------------------------------------------- read state
    def topic_states(self, student_id: int) -> dict[str, dict]:
        rows = self.conn.execute("SELECT * FROM topic_state WHERE student_id = ?", (student_id,)).fetchall()
        states = {r["topic"]: dict(r) for r in rows}
        for t in config.TOPICS:  # in case topics were added later
            states.setdefault(t, {"topic": t, "mastery": 0.0, "attempts": 0, "lessons_seen": 0,
                                  "examples_seen": 0, "attempts_since_lesson": 0, "last_activity": None})
        return states

    def attempts(self, student_id: int, topic: str | None = None) -> list[dict]:
        q = "SELECT * FROM attempts WHERE student_id = ?"
        args: list = [student_id]
        if topic:
            q += " AND topic = ?"
            args.append(topic)
        rows = self.conn.execute(q + " ORDER BY id", args).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["mistakes"] = json.loads(d["mistakes"])
            out.append(d)
        return out

    def weak_concepts(self, student_id: int, topic: str, top: int = 3) -> list[str]:
        counter: Counter = Counter()
        for a in self.attempts(student_id, topic)[-8:]:   # recent attempts only
            counter.update(a["mistakes"])
        return [m for m, _ in counter.most_common(top)]

    def activity_scores(self, student_id: int, topic: str) -> dict[str, float]:
        """Average score per practice activity type for a topic."""
        sums: dict[str, list[float]] = {}
        for a in self.attempts(student_id, topic):
            sums.setdefault(a["activity"], []).append(a["score"])
        return {k: sum(v) / len(v) for k, v in sums.items()}

    # ------------------------------------------------------------ write state
    def _ensure(self, student_id: int, topic: str):
        self.conn.execute(
            "INSERT OR IGNORE INTO topic_state (student_id, topic, updated_at) VALUES (?, ?, ?)",
            (student_id, topic, _now()),
        )

    def record_lesson(self, student_id: int, topic: str, kind: str = "lesson"):
        self._ensure(student_id, topic)
        if kind == "worked_example":
            sets = "examples_seen = examples_seen + 1"
        else:
            sets = "lessons_seen = lessons_seen + 1, attempts_since_lesson = 0"
        self.conn.execute(
            f"UPDATE topic_state SET {sets}, last_activity = ?, updated_at = ? "
            "WHERE student_id = ? AND topic = ?",
            (kind, _now(), student_id, topic),
        )
        self.conn.commit()

    def record_attempt(self, student_id: int, topic: str, activity: str, difficulty: str,
                       score: float, hints_used: int = 0, mistakes: list[str] | None = None) -> float:
        """Store a graded attempt and update topic mastery. Returns the new mastery."""
        score = max(0.0, min(1.0, float(score)))
        self._ensure(student_id, topic)
        self.conn.execute(
            "INSERT INTO attempts (student_id, topic, activity, difficulty, score, hints_used, mistakes, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (student_id, topic, activity, difficulty, score, hints_used, json.dumps(mistakes or []), _now()),
        )
        state = self.topic_states(student_id)[topic]
        a = config.MASTERY_ALPHA
        # harder questions count a little more toward mastery
        weight = {"easy": 0.85, "medium": 1.0, "hard": 1.15}.get(difficulty, 1.0)
        mastery = (1 - a) * state["mastery"] + a * min(1.0, score * weight)
        self.conn.execute(
            "UPDATE topic_state SET mastery = ?, attempts = attempts + 1, attempts_since_lesson = attempts_since_lesson + 1, "
            "last_activity = ?, updated_at = ? "
            "WHERE student_id = ? AND topic = ?",
            (mastery, activity, _now(), student_id, topic),
        )
        self.conn.commit()
        return mastery

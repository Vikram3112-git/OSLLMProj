"""
OSLLM web server (FastAPI). Serves the web interface in web/ and a small JSON API.

Run:  bash run.sh           (or:  python server.py)   then open http://localhost:8501
"""
from __future__ import annotations

import base64
import binascii
import json
import random
import re
import threading
import uuid
from pathlib import Path
from typing import Iterator

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
from core import emotion, problems, prompts, task_practice, variety
from core.evaluator import Evaluator
from core.llm import LLM, LLMError
from core.planner import ACTIVITY_LABELS, LearningPlanner, difficulty_for, is_mastered, practice_types
from core.problem_generator import ProblemGenerator
from core.profile_db import ProfileDB
from core import rag
from core.rag import Retriever
from core.topic_map import topic_for
from core.scheduler_engine import ALGORITHMS, ScheduleResult
from core.topic_guard import check_topic
from core.tutor import Tutor

WEB = Path(__file__).resolve().parent / "web"
app = FastAPI(title="OSLLM", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=WEB), name="static")

llm, db = LLM(), ProfileDB()


@app.on_event("startup")
def warm_up():
    """Load the embedding model, the index and the LLM in the background while the page opens."""
    def run():
        try:
            parts()["retriever"].retrieve("round robin time quantum", k=1)   # loads BGE + FAISS
        except Exception:
            pass
        llm.warm_up()
    threading.Thread(target=run, daemon=True).start()
_lock = threading.Lock()
_parts: dict = {}
ITEMS: dict[str, dict] = {}            # practice items waiting for an answer (kept in memory)
INDEXING = {"busy": False, "message": "", "error": ""}   # background re-indexing state

def parts():
    """Load the retriever (and embedding model) once, on first use."""
    with _lock:
        if not _parts:
            retriever = Retriever()
            _parts.update(retriever=retriever, tutor=Tutor(llm, retriever),
                          generator=ProblemGenerator(llm, retriever), evaluator=Evaluator(llm, retriever),
                          planner=LearningPlanner(db))
    return _parts


# ------------------------------------------------------------------ serialisers
def ser_solution(r: ScheduleResult) -> dict:
    return {"algorithm": r.algorithm, "name": ALGORITHMS[r.algorithm], "time_quantum": r.time_quantum,
            "gantt": [{"pid": s.pid, "start": s.start, "end": s.end} for s in r.gantt],
            "table": r.table, "steps": r.steps, "avg_tat": round(r.avg_tat, 2), "avg_wt": round(r.avg_wt, 2),
            "avg_rt": round(r.avg_rt, 2), "throughput": round(r.throughput, 3),
            "cpu_utilization": round(r.cpu_utilization, 3)}


def ser_problem(p: dict, with_solution: bool = True) -> dict:
    out = {"algorithm": p["algorithm"], "name": ALGORITHMS[p["algorithm"]], "processes": p["processes"],
           "time_quantum": p.get("time_quantum"), "scenario": p.get("scenario", ""),
           "with_priority": p["algorithm"].startswith("PRIORITY")}
    if with_solution:
        out["solution"] = ser_solution(p["solution"])
    return out


def ser_chunks(chunks) -> list[dict]:
    seen, out = set(), []
    for c in chunks or []:
        key = (c.source, c.page)
        if key in seen:
            continue
        seen.add(key)
        out.append({"source": c.source, "page": c.page, "url": c.url, "origin": c.origin,
                    "excerpt": c.text[:260] + ("..." if len(c.text) > 260 else "")})
    return out


def line(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str) + "\n"


def stream_text(stream: Iterator[str]) -> Iterator[str]:
    for piece in stream:
        if piece:
            yield line({"type": "token", "text": piece})


def ndjson(gen: Iterator[str]) -> StreamingResponse:
    return StreamingResponse(gen, media_type="application/x-ndjson",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ------------------------------------------------------------------ pages
@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


@app.get("/api/status")
def status():
    ok, msg = llm.health()
    kb = {"ready": config.INDEX_PATH.exists(), "chunks": 0, "universal": 0, "sources": []}
    if kb["ready"]:
        chunks = rag.read_chunks()
        kb["chunks"] = len(chunks)
        kb["universal"] = sum(1 for c in chunks if c.get("origin") == "universal")
        names = {}
        for c in chunks:
            names.setdefault(c["source"], {"source": c["source"], "url": c.get("url"),
                                           "origin": c.get("origin", "course notes")})
        kb["sources"] = sorted(names.values(), key=lambda s: (s["origin"] != "course notes", s["source"]))
    return {"llm_ok": ok, "llm": msg, "model": config.LLM_MODEL, "kb": kb, "topics": config.TOPICS,
            "units": [{"unit": u, "topics": t} for u, t in config.UNITS], "indexing": dict(INDEXING),
            "numerical_topics": config.NUMERICAL_TOPICS, "algorithms": ALGORITHMS,
            "practice_types": {t: practice_types(t) for t in config.TOPICS}, "activity_labels": ACTIVITY_LABELS}


# ------------------------------------------------------------------ chat
class ChatIn(BaseModel):
    student: str
    message: str
    history: list[dict] = []
    mode: str = "teach"                 # "teach" (structured lessons) or "talk" (conversational)


@app.post("/api/mood")
def mood(body: ChatIn):
    """Live preview of the mood reading while the student types."""
    return emotion.read(body.message, body.history).to_dict()



# ------------------------------------------------------------------ variety (no repeated answers)
def topic_of(algo: str) -> str:
    return next(t for t, algos in config.NUMERICAL_TOPICS.items() if algo in algos)


def variety_note(sess, followup: bool, history: list[dict]) -> tuple[str, float]:
    """A teaching angle not used in the last few answers; for follow-ups also the previous answer to avoid."""
    _, angle = variety.pick_angle(sess)
    note = f"TEACHING ANGLE for this answer: {angle}"
    if not followup:
        return note, 0.4
    prev = next((m.get("content", "") for m in reversed(history or []) if m.get("role") == "assistant"), "")
    prev = " ".join(prev.split())[:500]
    note += "\n" + prompts.FOLLOW_UP_NOTE.format(prev=f' (it began: "{prev}")' if prev else "")
    return note, 0.6


def remember(sess, plan: dict, process_sets: list[list[dict]], task_inputs: list[dict] | None = None):
    for rows in process_sets:
        if rows:
            sess.seen.add(variety.procs_key(rows))
    for inp in task_inputs or []:
        if inp:
            sess.seen.add(problems.key(inp))
    if plan.get("algos"):
        sess.last_algos = list(plan["algos"])
    sess.last_kind = plan["kind"]
    sess.last_domain = plan.get("domain")

@app.post("/api/chat")
def chat(body: ChatIn):
    """The OSLLM request pipeline:

        Student -> Web interface -> this backend -> mood + topic check -> Request router
            |-- RAG pipeline ("Teach me"): query embedding (BGE) -> FAISS -> relevant chunks
            |-- Automatic tone adaptation from the student's message and conversation
        -> (scheduling engine for exact numbers) -> prompt construction -> Ollama (local)
        -> streaming response -> Student

    The stages actually used are sent back in the "done" event as `path`, and the web page shows them.
    """
    question = body.message.strip()
    if not question:
        raise HTTPException(400, "Type a question first.")
    # Always use the course-aware retrieval path. Answer style adapts automatically to the message.
    plain = False

    def run():
        path = ["Web interface", "Python backend (FastAPI)"]
        reading = emotion.read(question, body.history)
        style = emotion.style_instruction(reading)
        mood = reading.to_dict()
        path.append(f"Mood: {mood.get('label') or reading.mood}")
        yield line({"type": "mood", **mood})

        engine_name_ref = ["Scheduling engine"]

        def finish(kind: str, chunks=None, engine: bool = False, retrieval: bool = True):
            """Complete the path for this answer: retrieval -> engine -> prompt -> model -> stream."""
            if retrieval and not plain:
                path.extend(["RAG pipeline", "Query embedding (BGE)", f"FAISS search: {len(chunks or [])} chunks"])
            else:
                path.append("Direct response (social message)")
            if engine:
                path.append(f"{engine_name_ref[0]} (exact numbers)")
            path.extend(["Prompt construction", f"Ollama: {llm.model} (local)", "Streaming response"])
            return line({"type": "done", "kind": kind, "path": path})

        try:
            p = parts()
            tutor = p["tutor"]

            # greetings, thanks, feelings: answered directly, no retrieval
            if reading.social:
                path.append("Router: social")
                stream, _ = tutor.stream_social(question, reading.to_dict(), body.history, style)
                yield from stream_text(stream)
                yield finish("social", retrieval=False)
                return

            on_topic, refusal = check_topic(question, llm, body.history)
            if not on_topic:
                if reading.mood in ("frustrated", "anxious", "tired"):
                    refusal = "I can tell you've got a lot going on. " + refusal
                yield line({"type": "token", "text": refusal})
                path.append("Topic guard: declined (outside process scheduling)")
                yield line({"type": "done", "kind": "off_topic", "path": path})
                return
            path.append("Topic guard: on topic")

            sess = variety.session(body.student)
            plan = tutor.route(question, body.history, sess)
            path.append(f"Router: {ROUTE_NAMES.get(plan['kind'], plan['kind'])}"
                        + (f", {problems.DOMAIN_NAMES[plan['domain']]}" if plan["domain"] in problems.DOMAIN_NAMES else "")
                        + (" (follow-up)" if plan["followup"] else ""))
            engine_name_ref[0] = ENGINE_NAMES.get(plan["domain"], "Scheduling engine")
            note, temp = variety_note(sess, plan["followup"], body.history)
            if plan["note"]:
                yield line({"type": "note", "text": plan["note"]})

            if plan["domain"] not in ("cpu", "general") and plan["kind"] != "concept":
                # Banker's algorithm, page replacement, disk scheduling or memory allocation
                dom = plan["domain"]
                if plan["kind"] == "series":
                    shown, all_chunks = [], []
                    for i, (label, algo, inp) in enumerate(plan["runs"], 1):
                        inp = inp or problems.design(dom, algo, sess.seen | {problems.key(x) for x in shown})
                        shown.append(inp)
                        solved = tutor.solve_task(algo, inp)
                        yield line({"type": "section", "title": f"{i}. {solved.name}"})
                        yield line({"type": "task", **solved.to_dict()})
                        stream, chunks = tutor.stream_task_step(solved, i, len(plan["runs"]), question, style,
                                                                note, temp, plain)
                        all_chunks += [c for c in chunks if c not in all_chunks]
                        yield from stream_text(stream)
                    remember(sess, plan, [], shown)
                    yield line({"type": "sources", "items": ser_chunks(all_chunks[:6])})
                    yield finish("series", all_chunks, engine=True)
                    return
                if plan["kind"] == "compare":
                    common = None
                    if any(inp is None for _, _, inp in plan["runs"]):
                        common = problems.design(dom, None, sess.seen)
                    runs = [(label, algo, inp or common) for label, algo, inp in plan["runs"]]
                    solved = [tutor.solve_task(algo, inp) for _, algo, inp in runs]
                    yield line({"type": "task_compare", "domain": dom, "labels": [r[0] for r in runs],
                                "items": [x.to_dict() for x in solved]})
                    stream, chunks = tutor.stream_task_compare(solved, [r[0] for r in runs], question, plan["focus"],
                                                               style, note, temp, plain)
                    remember(sess, plan, [], [r[2] for r in runs])
                else:
                    label, algo, inp = plan["runs"][0]
                    inp = inp or problems.design(dom, algo, sess.seen)
                    solved = tutor.solve_task(algo, inp)
                    level = "beginner" if reading.mood in ("confused", "frustrated", "tired", "anxious") else "standard"
                    yield line({"type": "task", **solved.to_dict()})
                    stream, chunks = tutor.stream_task(solved, question, level, plan["focus"], style, note, temp, plain)
                    remember(sess, plan, [], [inp])
                engine = True

            elif plan["kind"] == "compare":
                comp = tutor.build_comparison(plan["processes"], plan["runs"])
                yield line({"type": "comparison", "processes": comp["processes"],
                            "with_priority": comp["with_priority"],
                            "results": [{"label": r["label"], "switches": r["switches"],
                                         "solution": ser_solution(r["solution"])} for r in comp["results"]]})
                stream, chunks = tutor.stream_comparison(comp, question, plan["focus"], style, note, temp, plain)
                remember(sess, plan, [plan["processes"]])
                engine = True

            elif plan["kind"] == "series":
                # a separate, freshly designed example for each algorithm, each explained on its own
                shown, all_chunks = [], []
                for i, (label, algo, q) in enumerate(plan["runs"], 1):
                    rows, q2 = variety.design(algo, sess.seen | {variety.procs_key(r) for r in shown}, quantum=q)
                    problem = tutor.build_problem(rows, algo, q2, topic_of(algo))
                    shown.append(rows)
                    yield line({"type": "section", "title": f"{i}. {ALGORITHMS[algo]}"
                                + (f" (q = {q2})" if algo == "RR" else "")})
                    yield line({"type": "example", **ser_problem(problem)})
                    stream, chunks = tutor.stream_series_step(problem, i, len(plan["runs"]), question, style,
                                                              note, temp, plain)
                    all_chunks += [c for c in chunks if c not in all_chunks]
                    yield from stream_text(stream)
                remember(sess, plan, shown)
                yield line({"type": "sources", "items": ser_chunks(all_chunks[:6])})
                yield finish("series", all_chunks, engine=True)
                return

            elif plan["kind"] == "example":
                algo, q = plan["algorithm"], plan["time_quantum"]
                if plan["processes"]:
                    problem = tutor.build_problem(plan["processes"], algo, q, topic_of(algo))
                else:   # a new example designed for this algorithm, never one this student has already seen
                    rows, q2 = variety.design(algo, sess.seen, quantum=plan["user_quantum"])
                    problem = tutor.build_problem(rows, algo, q2, topic_of(algo))
                level = "beginner" if reading.mood in ("confused", "frustrated", "tired", "anxious") else "standard"
                yield line({"type": "example", **ser_problem(problem)})
                stream, chunks = tutor.stream_worked_example(problem, problem["solution"], level,
                                                             request=question, focus=plan["focus"], style=style,
                                                             note=note, temperature=temp, plain=plain)
                remember(sess, plan, [problem["processes"]])
                engine = True

            else:
                stream, chunks = tutor.stream_answer(question, body.history, style, note, temp, plain)
                remember(sess, plan, [])
                engine = False

            yield line({"type": "sources", "items": ser_chunks(chunks)})
            yield from stream_text(stream)
            yield finish(plan["kind"], chunks, engine=engine)
        except FileNotFoundError:
            yield line({"type": "error", "text": "The knowledge base isn't built yet. Run `bash run.sh` again."})
        except LLMError as e:
            yield line({"type": "error", "text": f"{e} Check that Ollama is running."})
        except Exception as e:  # keep the interface alive and say what happened
            yield line({"type": "error", "text": f"Something went wrong: {e}"})

    return ndjson(run())


ROUTE_NAMES = {"concept": "explanation", "example": "worked example", "compare": "comparison",
               "series": "separate examples"}
ENGINE_NAMES = {"cpu": "Scheduling engine", "bankers": "Banker's solver", "page": "Page replacement solver",
                "disk": "Disk scheduling solver", "alloc": "Memory allocation solver"}


# ------------------------------------------------------------------ your own files
def _reload_retriever():
    """Point every component at the freshly built index."""
    with _lock:
        if _parts:
            r = Retriever()
            _parts["retriever"] = r
            for k in ("tutor", "generator", "evaluator"):
                _parts[k].retriever = r


def _index_job(message: str, paths: list | None = None):
    def job():
        INDEXING.update(busy=True, message=message, error="")
        try:
            n = rag.add_files(paths) if paths else rag.build_index()
            _reload_retriever()
            INDEXING.update(message=f"Done: {n} new chunks indexed." if paths else f"Done: {n} chunks indexed.")
        except Exception as e:  # keep the app usable and report the problem
            INDEXING.update(error=f"Indexing failed: {e}")
        finally:
            INDEXING["busy"] = False
    threading.Thread(target=job, daemon=True).start()


def _safe_name(name: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._ -]+", "_", Path(name).name).strip(" .") or "file"
    return stem[:120]


@app.get("/api/files")
def list_files():
    config.MY_FILES_DIR.mkdir(parents=True, exist_ok=True)
    counts = {}
    if config.CHUNKS_PATH.exists():
        for c in rag.read_chunks():
            counts[c["source"]] = counts.get(c["source"], 0) + 1
    files = [{"name": f.name, "kb": round(f.stat().st_size / 1024), "chunks": counts.get(f.name, 0)}
             for f in sorted(config.MY_FILES_DIR.iterdir()) if f.suffix.lower() in rag.SUPPORTED]
    return {"files": files, "indexing": dict(INDEXING)}


class FileIn(BaseModel):
    name: str
    data: str                            # base64 file content


@app.post("/api/files")
def upload_file(body: FileIn):
    if INDEXING["busy"]:
        raise HTTPException(409, "Indexing is already running. Try again in a minute.")
    name = _safe_name(body.name)
    if Path(name).suffix.lower() not in rag.SUPPORTED:
        raise HTTPException(400, "Only PDF, Markdown (.md) and text (.txt) files can be added.")
    try:
        raw = base64.b64decode(body.data.split(",")[-1], validate=False)
    except (ValueError, binascii.Error):
        raise HTTPException(400, "The file could not be read.")
    if len(raw) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"Files must be under {config.MAX_UPLOAD_MB} MB.")
    if name.lower().endswith(".pdf") and not raw.startswith(b"%PDF"):
        raise HTTPException(400, "That does not look like a PDF file.")
    config.MY_FILES_DIR.mkdir(parents=True, exist_ok=True)
    path = config.MY_FILES_DIR / name
    path.write_bytes(raw)
    _index_job(f"Adding {name} to the knowledge base...", [path])
    return {"ok": True, "name": name}


@app.delete("/api/files/{name}")
def delete_file(name: str):
    if INDEXING["busy"]:
        raise HTTPException(409, "Indexing is running. Try again in a minute.")
    path = config.MY_FILES_DIR / _safe_name(name)
    if not path.exists():
        raise HTTPException(404, "No such file.")
    path.unlink()
    _index_job(f"Removing {path.name} and rebuilding the knowledge base...")
    return {"ok": True}


@app.post("/api/reindex")
def reindex():
    if INDEXING["busy"]:
        raise HTTPException(409, "Indexing is already running.")
    _index_job("Rebuilding the whole knowledge base...")
    return {"ok": True}


@app.get("/api/topic_for")
def api_topic_for(text: str):
    return {"topic": topic_for(text)}


# ------------------------------------------------------------------ learn
class LearnIn(BaseModel):
    student: str
    topic: str
    level: str = "medium"
    kind: str = "lesson"                 # lesson | worked_example | relearn
    algorithm: str | None = None


@app.post("/api/learn")
def learn(body: LearnIn):
    if body.topic not in config.TOPICS:
        raise HTTPException(400, "Unknown topic.")

    def run():
        try:
            p = parts()
            sid = db.get_or_create_student(body.student)
            if body.kind == "worked_example" and body.topic in config.NUMERICAL_TOPICS:
                sess = variety.session(body.student)
                algo = body.algorithm or random.choice(config.NUMERICAL_TOPICS[body.topic])
                if algo in config.CPU_ALGOS:
                    problem = p["generator"].numerical(body.topic, body.level, algo)
                    yield line({"type": "example", **ser_problem(problem)})
                    stream, chunks = p["tutor"].stream_worked_example(problem, problem["solution"], body.level)
                else:
                    item = p["generator"].task(body.topic, body.level, algo, sess.seen)
                    sess.seen.add(problems.key(item["inputs"]))
                    yield line({"type": "task", **item["solved"].to_dict()})
                    level = {"easy": "beginner", "medium": "standard", "hard": "advanced"}.get(body.level, "standard")
                    stream, chunks = p["tutor"].stream_task(item["solved"], f"Worked example on {body.topic}", level)
            else:
                weak = db.weak_concepts(sid, body.topic) if body.kind == "relearn" else None
                stream, chunks = p["tutor"].stream_lesson(body.topic, body.level, weak,
                                                           sess=variety.session(body.student))
            yield line({"type": "sources", "items": ser_chunks(chunks)})
            yield from stream_text(stream)
            yield line({"type": "done"})
        except LLMError as e:
            yield line({"type": "error", "text": f"{e} Check that Ollama is running."})
        except Exception as e:
            yield line({"type": "error", "text": f"Something went wrong: {e}"})

    return ndjson(run())


class DoneIn(BaseModel):
    student: str
    topic: str
    kind: str = "lesson"


@app.post("/api/learn/done")
def learn_done(body: DoneIn):
    db.record_lesson(db.get_or_create_student(body.student), body.topic, body.kind)
    return {"ok": True}


# ------------------------------------------------------------------ practice
class NewItemIn(BaseModel):
    student: str
    topic: str | None = None
    kind: str | None = None
    difficulty: str = "auto"
    algorithm: str | None = None
    force_practice: bool = False


@app.post("/api/practice/new")
def practice_new(body: NewItemIn):
    p = parts()
    sid = db.get_or_create_student(body.student)
    reason = ""
    if not body.topic:                                  # let the planner choose
        plan = p["planner"].next_activity(sid)
        reason = plan.reason
        if plan.activity in ("lesson", "relearn", "worked_example") and not body.force_practice:
            return {"plan": {"activity": plan.activity, "label": ACTIVITY_LABELS[plan.activity],
                             "topic": plan.topic, "difficulty": plan.difficulty, "reason": plan.reason}}
        # "Pick for me" means pick a quiz, not redirect the learner to a lesson.
        # If the planner's next step is a lesson, use its topic but generate a
        # practice item of a supported type instead.
        topic = plan.topic
        kind = plan.activity if plan.activity in practice_types(topic) else practice_types(topic)[0]
        diff = body.difficulty if body.difficulty != "auto" else plan.difficulty
    else:
        topic = body.topic
        kind = body.kind or practice_types(topic)[0]
        diff = body.difficulty
        if diff == "auto":
            diff = difficulty_for(db.topic_states(sid)[topic]["mastery"])
    weak = db.weak_concepts(sid, topic)
    try:
        if kind == "mcq":
            item = p["generator"].mcq(topic, diff, weak)
            public = {"question": item["question"], "options": item["options"], "has_hint": True}
        elif kind == "viva":
            item = p["generator"].viva(topic, diff, weak)
            public = {"question": item["question"], "hint_count": len(item["hints"])}
        elif kind == "numerical":
            item = p["generator"].numerical(topic, diff, body.algorithm)
            if item.get("task"):
                sv = item["solved"]
                public = {"task": {"kind": sv.kind, "algorithm": sv.algorithm, "name": sv.name, "inputs": sv.inputs,
                                   "problem": sv.problem_text()}, "ask": task_practice.ask_fields(sv)}
            else:
                public = ser_problem(item, with_solution=False)
        else:
            raise HTTPException(400, "Unknown question type.")
    except LLMError as e:
        raise HTTPException(503, f"{e} Check that Ollama is running.")
    item_id = uuid.uuid4().hex[:10]
    ITEMS[item_id] = {"student": body.student, "sid": sid, "topic": topic, "kind": kind, "difficulty": diff,
                      "item": item, "hints": [], "done": False}
    return {"id": item_id, "topic": topic, "kind": kind, "label": ACTIVITY_LABELS[kind], "difficulty": diff,
            "reason": reason, **public}


class IdIn(BaseModel):
    id: str


def _get(item_id: str) -> dict:
    if item_id not in ITEMS:
        raise HTTPException(404, "That question has expired. Start a new one.")
    return ITEMS[item_id]


@app.post("/api/practice/hint")
def practice_hint(body: IdIn):
    rec = _get(body.id)
    item, kind = rec["item"], rec["kind"]
    if kind == "mcq":
        if rec["hints"]:
            raise HTTPException(400, "MCQs have one hint.")
        hint = item.get("hint", "")
    elif kind == "viva":
        if len(rec["hints"]) >= len(item["hints"]):
            raise HTTPException(400, "No more hints.")
        hint = item["hints"][len(rec["hints"])]
    elif item.get("task"):
        if len(rec["hints"]) >= 3:
            raise HTTPException(400, "No more hints.")
        hint = task_practice.hint(item["solved"], len(rec["hints"]) + 1)
    else:
        if len(rec["hints"]) >= 3:
            raise HTTPException(400, "No more hints.")
        try:
            hint = parts()["evaluator"].numerical_hint(item, len(rec["hints"]) + 1)
        except LLMError as e:
            raise HTTPException(503, str(e))
    rec["hints"].append(hint)
    return {"hint": hint, "used": len(rec["hints"])}


class SubmitIn(BaseModel):
    id: str
    choice: int | None = None           # MCQ
    answer: str | None = None           # viva
    gantt: str | None = None            # numerical
    rows: dict | None = None
    avg_tat: float | None = None
    avg_wt: float | None = None
    answers: dict | None = None         # numericals outside CPU scheduling
    reveal: bool = False


@app.post("/api/practice/submit")
def practice_submit(body: SubmitIn):
    rec = _get(body.id)
    if rec["done"]:
        raise HTTPException(400, "Already answered. Start a new question.")
    item, kind = rec["item"], rec["kind"]
    hints = len(rec["hints"])
    out: dict = {"kind": kind}
    try:
        if body.reveal:
            res = {"score": 0.0, "mistakes": [f"{rec['topic']} procedure"], "feedback": "", "revealed": True}
        elif kind == "mcq":
            # MCQ marking is deliberately independent of Ollama and the evaluator.
            # This path must remain fast even if model inference is slow or unavailable.
            if body.choice is None:
                raise HTTPException(400, "Pick an option first.")
            if not isinstance(body.choice, int) or not 0 <= body.choice < len(item.get("options", [])):
                raise HTTPException(400, "That option is invalid. Choose an answer and try again.")
            answer_index = int(item["answer_index"])
            correct = body.choice == answer_index
            score = 1.0 if correct else 0.0
            score = max(0.0, score * (1 - config.HINT_PENALTY * hints))
            correct_letter = chr(65 + answer_index)
            chosen_letter = chr(65 + body.choice)
            explanation = (item.get("explanation") or "Compare the definition with the conditions stated in the question.").strip()
            if correct:
                feedback = f"Your answer ({chosen_letter}) is correct. {explanation}"
            else:
                feedback = (f"Your answer: {chosen_letter}) {item['options'][body.choice]}. "
                            f"Correct answer: {correct_letter}) {item['options'][answer_index]}. {explanation}")
            res = {"correct": correct, "score": score,
                   "mistakes": [] if correct else [item.get("concept", rec["topic"])],
                   "feedback": feedback, "points_earned": round(score, 2), "points_possible": 1}
        else:
            ev = parts()["evaluator"]
            if kind == "viva":
                res = ev.viva(item, body.answer or "", hints)
            elif item.get("task"):
                res = task_practice.check(item["solved"], body.answers or {})
                res["score"] = max(0.0, res["score"] - config.HINT_PENALTY * hints)
            else:
                res = ev.numerical(item, {"gantt": body.gantt or "", "rows": body.rows or {},
                                          "avg_tat": body.avg_tat, "avg_wt": body.avg_wt}, hints)
    except LLMError as e:
        raise HTTPException(503, f"{e} Check that Ollama is running.")
    rec["done"] = True
    mastery = db.record_attempt(rec["sid"], rec["topic"], kind, rec["difficulty"], res["score"], hints,
                                res.get("mistakes", []))
    out.update({k: v for k, v in res.items() if k not in ("cells",)})
    out["cells"] = res.get("cells")
    out["mastery"] = round(mastery, 3)
    if kind == "mcq":
        out["answer_index"] = item["answer_index"]
        out["explanation"] = item.get("explanation", "")
    elif kind == "viva":
        out["model_answer"] = item.get("model_answer", "")
        out["key_points"] = item["key_points"]
    elif item.get("task"):
        out["task"] = item["solved"].to_dict()
    else:
        out["solution"] = ser_solution(item["solution"])
    return JSONResponse(json.loads(json.dumps(out, default=str)))


# ------------------------------------------------------------------ progress
@app.get("/api/progress")
def progress(student: str):
    sid = db.get_or_create_student(student)
    states = db.topic_states(sid)
    attempts = db.attempts(sid)
    topics = []
    for t in config.TOPICS:
        st = states[t]
        topics.append({"topic": t, "mastery": round(st["mastery"], 3), "attempts": st["attempts"],
                       "lessons": st["lessons_seen"], "mastered": is_mastered(st),
                       "weak": db.weak_concepts(sid, t)})
    plan = LearningPlanner(db).next_activity(sid)
    return {"topics": topics, "attempts": attempts[-40:], "total_attempts": len(attempts),
            "average": round(sum(a["score"] for a in attempts) / len(attempts), 3) if attempts else None,
            "next": {"activity": plan.activity, "label": ACTIVITY_LABELS[plan.activity], "topic": plan.topic,
                     "difficulty": plan.difficulty, "reason": plan.reason}}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="127.0.0.1", port=8501, log_level="warning")

# OSLLM - an Operating Systems tutor that runs on your laptop

A learning system for the whole **Operating Systems course (BCSE303L)**: OS structure and system
calls, processes, threads and IPC, CPU scheduling, process synchronization, deadlocks, memory
management, virtual memory, file systems, disk scheduling and Linux commands. It runs a local
instruction-tuned LLM (Qwen3 8B through Ollama), retrieves from our course notes plus openly
licensed textbooks and documentation, solves every numerical exactly with its own solvers, senses
the student's mood and tone, and adapts every answer to them.
Vikram Kumar (24BCE0720) and P Nithish Kumar (24BCE0757).

## How a question flows

```
Student
  -> Web interface (HTML / CSS / JS, web/)
  -> Python backend (FastAPI, server.py)
  -> Mood + topic check (core/emotion.py, core/topic_guard.py: anything in the OS course is answered)
  -> Request router (core/tutor.py): which unit, and explanation / worked example / comparison / series
       |-- RAG pipeline ("Teach me"):  query embedding (BGE) -> FAISS -> relevant study chunks
       |-- Plain AI mode ("Just talk", greetings): no retrieval
  -> Exact solvers for numericals
       CPU scheduling      core/scheduler_engine.py  (Gantt chart, CT/TAT/WT/RT, decision trace)
       Banker's, deadlock detection, page replacement, disk scheduling, memory allocation
                           core/os_solvers.py        (every step, with the reason for it)
  -> Prompt construction (core/prompts.py, core/variety.py)
  -> Ollama: Qwen3-8B on this computer (osllm, or osllm-ft after fine-tuning)
  -> Streaming response -> Student
```

Every answer in the chat has a "How this was answered" line that lists the stages it actually went through.
The model explains; it never invents the numbers. Those always come from the solvers.

## Run on Windows, macOS, or Linux

See **[README_PORTABLE.md](README_PORTABLE.md)** for beginner-friendly, step-by-step setup and troubleshooting for all three operating systems.

- Windows: install Python 3.10+ and Ollama, then double-click `run.bat`.
- macOS: install and open Ollama, then run `./run.sh` in Terminal.
- Linux: run `./run.sh` in Terminal (the launcher attempts to install Ollama if it is missing).

The first run needs internet access and several GB of disk space to download the local model, Python dependencies, and embedding model. Open http://localhost:8501 when the server starts. Use `fast` for the smaller/faster model or `quality` for more detailed answers on capable computers.

## What the solvers cover
| Unit | Numericals solved exactly | Conventions |
|---|---|---|
| CPU scheduling | FCFS, SJF, SRTF, Priority (both), Round Robin | ties: earlier arrival, then lower process number; lower number = higher priority |
| Deadlocks | Banker's safety check, resource request, deadlock detection | repeated passes in process order; any valid safe sequence is accepted |
| Memory | first, best, worst and next fit | the chosen hole is split; next fit resumes at the hole used last |
| Virtual memory | FIFO, LRU, Optimal page replacement; Belady's anomaly | OPT tie: among pages never used again, the one loaded first |
| Disk | FCFS, SSTF, SCAN, C-SCAN, LOOK, C-LOOK | SCAN / C-SCAN go to the edge; the C-SCAN / C-LOOK return jump is counted |

`finetune/verify_engine.py` checks the CPU engine against an independent tick simulator and OSTEP's
`scheduler.py`; `finetune/verify_solvers.py` checks the other solvers against separate reference
implementations (brute force for OPT, every permutation for Banker's), 2000 random problems each.

## Knowledge base
| Source | Licence | Where |
|---|---|---|
| Our course notes (14 documents, one or more per unit, with worked numbers and viva questions) | own work | `knowledge_base/*.md` |
| *Operating Systems: Three Easy Pieces* (Arpaci-Dusseau): 25 chapters across processes, scheduling, memory, concurrency and files; the authors' scheduling-simulator READMEs | free online material by the authors; downloaded for personal study, not redistributed | `knowledge_base/universal/book_ostep_*.md` |
| *Operating Systems and Middleware* (Hailperin; Open Textbook Library): Chapter 3, Scheduling | CC BY-SA 3.0 | `knowledge_base/universal/book_hailperin_*.md` |
| Microsoft Learn: Windows thread scheduling (7 pages) | CC BY 4.0 | `knowledge_base/universal/ms_*.md` |
| Linux man-pages: sched(7), fork(2), execve(2), wait(2), pthreads(7), sem_overview(7), pipe(7), shm_overview(7) and more | GPL-2.0+ | `knowledge_base/universal/man_*.md` |
| Linux kernel documentation: CFS, EEVDF, nice levels, scheduling domains, memory-management concepts | GPL-2.0 | `knowledge_base/universal/kernel_*.md` |
| Your own slides, notes and question papers | yours | add them on the **My files** page (saved in `knowledge_base/my_files/`) |

Files named `book_*` are downloaded on the first run (`bash run.sh sources` to refresh).
Retrieval is balanced: course notes and your own files come first (they match our conventions),
with at most two universal passages per answer. Every answer lists the passages it used, with links.

## Fine-tuning
`finetune/` builds a verified instruction dataset (about 8,300 training examples across all units:
CPU-scheduling solutions, Banker's / page / disk / memory numericals and comparisons, concept
answers, mistake diagnoses and mood-adapted answers; every number comes from the solvers), a Colab
notebook that fine-tunes Qwen3 with QLoRA and exports a GGUF file, and an evaluation script that
scores held-out numericals from every solver. See `finetune/README.md`.

```bash
bash run.sh dataset           # verify the engine and solvers, build finetune/data/
bash run.sh eval osllm        # score a model on held-out problems
```

## Mood and tone sensing
`core/emotion.py` reads each message and the recent conversation and detects:
- **mood**: confused, frustrated, anxious (exam stress), rushed, tired, curious, happy, or neutral
- **tone**: casual or formal
- **social messages**: greetings, thanks, or feelings that are not a question

The reading changes how the LLM answers. A confused student gets simpler words and one small
example; if they are still confused next turn, a completely different explanation. An anxious
student gets a calm, exam-focused answer with a revision checklist. A rushed student gets under
120 words. The interface shows the reading live while you type, and each reply opens with one
line saying how it adapted.

## No repeated answers
`core/variety.py` and `core/problems.py` keep the chat from giving the same answer twice:

- every example gets new numbers, designed and checked with the solvers so it shows what the algorithm is about
  (a convoy for FCFS, a real preemption for SRTF, a reference string where OPT beats LRU and LRU beats FIFO,
  a disk queue with requests on both sides of the head), and an input the student has already seen is never reused;
- "nope", "explain differently", "another example" are treated as follow-ups: same topic, new numbers, and the
  model is told not to repeat its previous answer;
- "...for all the algorithms with separate examples" gives each algorithm its own example and explanation;
- each answer uses one of seven teaching angles, never one of the last four.

## Interface
A custom web app (FastAPI + plain HTML/CSS/JS, no build step):
- **Chat**: the syllabus as a strip of nine units with starter questions; worked examples drawn
  for each solver (Gantt charts, Banker's tables and safe sequences, page-frame grids with every
  fault marked, disk head-movement plots, memory placement tables); side-by-side comparisons;
  edit, copy, regenerate and versions; source citations
- **Saved chats**: every conversation is kept in the browser (sidebar), reopened exactly as it was
- **Quiz me**: an MCQ, viva or numerical on the topic you were just talking about, answered and
  graded right inside the chat
- **Learn**: topics grouped by unit; lessons at three levels and worked examples
- **Practice**: MCQs, numericals for every solver with field-by-field checking, viva questions,
  progressive hints, and "Pick for me" from the learning planner
- **Progress**: mastery per topic grouped by unit, recurring mistakes, recent answers, next step
- **My files**: upload PDFs, Markdown or text; they are indexed on this computer and cited in answers

## Files
| Path | Purpose |
|---|---|
| `server.py` | Web server and API (chat, learn, practice, progress, my files) |
| `web/` | Interface (`index.html`, `style.css`, `app.js`) |
| `core/emotion.py` | Mood and tone sensing, style instructions |
| `core/tutor.py`, `core/prompts.py` | Query routing and teaching prompts |
| `core/topic_guard.py`, `core/topic_map.py` | Keeps OSLLM on the OS course; maps a request to a syllabus topic |
| `core/rag.py`, `ingest.py`, `fetch_sources.py` | Knowledge base: download, chunk, embed (BGE), index (FAISS), retrieve |
| `core/scheduler_engine.py` | CPU scheduling: exact Gantt charts, CT/TAT/WT/RT and decision traces |
| `core/os_solvers.py`, `core/problems.py` | Banker's, detection, page replacement, disk, memory allocation; reading and designing problems |
| `core/task_practice.py` | Checking and hints for the non-CPU numericals |
| `core/problem_generator.py`, `core/evaluator.py` | Practice questions and grading |
| `core/planner.py`, `core/profile_db.py` | Learning planner and student profile (SQLite) |
| `Modelfile`, `core/llm.py` | The osllm model on qwen3:8b, and the Ollama client |
| `test_osllm.py` | Test suite across all units |
| `chunk_stats.py` | Measures the knowledge base after chunking |
| `solve.py` | Solves a scheduling problem in the terminal without the LLM, e.g. `python solve.py RR "P1 0 5, P2 1 4" -q 2` |
| `finetune/` | Dataset builder, engine and solver verification, Colab notebook, evaluation |

# OSLLM adaptive tutor update

## What changed
- Removed the **Just talk** toggle. Chat always uses the course-aware retrieval pipeline when answering OS questions.
- The tutor adapts explanation style automatically to writing cues and conversation context; it should not label or diagnose the user's emotions.
- Updated system and answer prompts to start with the actual answer, explain the requested concept fully, and include only directly related context.
- Added explicit instructions against exposing internal planning, word counts, prompt interpretation, or self-commentary such as “I should start with…” and “So the answer is…”.
- Removed the automatic “check yourself” question from general chat answers unless a follow-up genuinely helps. Dedicated Learn and Practice flows remain unchanged.

## Linux update
1. Stop the currently running OSLLM server with `Ctrl+C` in its terminal.
2. Back up the existing project folder if you have local files or settings you want to keep.
3. Extract this ZIP to a new folder, or replace the project code files with the updated copies.
4. From the extracted `OSLLM` folder, run:

   ```bash
   chmod +x run.sh
   ./run.sh
   ```
5. Refresh `http://localhost:8501` with `Ctrl+Shift+R`.

The first response may still be slower while the local model is loaded. These prompt/UI changes improve response focus and behavior; they do not guarantee a specific inference speed.

## Adaptive answer quality and source coverage update

- Strengthened the tutor's answer policy: answer directly, never narrate planning or comment on the student's mood, and provide detailed explanations when requested.
- Course notes remain the syllabus guide, but are no longer treated as the boundary of knowledge. Standard OS textbook/reference knowledge and the indexed universal source collection should fill gaps.
- Open-ended chat retrieves up to six relevant passages, including up to four from universal sources, to improve coverage for broad questions.
- Streaming output now suppresses common internal-planning paragraphs that smaller local models sometimes accidentally emit as ordinary text. Explicit `<think>` blocks remain hidden too.
- The universal-source collection is local and pre-indexed during first-run setup; internet access is required during initial setup to fetch reference material. This is not unrestricted live web search.


## Practice checker hang fix (2026-10-24)
- MCQ grading is now deterministic and immediate, including wrong answers; it no longer waits for an LLM-generated explanation.
- Browser API requests now time out after 25 seconds and show a recoverable error instead of spinning indefinitely.
- If the UI still hangs after this update, restart the server and hard-refresh the browser (Ctrl+Shift+R) to avoid cached JavaScript.


## Free-order practice and clearer marking (2026-10-24)
- Learners can choose any topic, question type and difficulty without completing lessons in a prescribed sequence. Planner recommendations are optional.
- Progress now offers both **Start recommendation** and **Practice this topic now**.
- MCQ checking is handled directly by the API and does not initialize or call the LLM evaluator. Correctness, the correct option, explanation and marks are returned deterministically.
- MCQ feedback displays points earned out of one and makes the hint deduction visible. Invalid choices return a recoverable error.
- The frontend asset version is bumped so a browser refresh loads the updated checker instead of stale JavaScript.

## If the browser still shows “Checking…”
1. Stop the running app in its terminal with `Ctrl+C`.
2. Extract and launch this updated ZIP (do not keep running the old project folder).
3. Run `./run.sh` from the extracted `OSLLM` directory.
4. Open `http://localhost:8501` and press `Ctrl+Shift+R`.
5. If it persists, check the terminal for a Python traceback and share that output; the screenshot alone cannot identify a remaining backend error.


## Fix: Pick for me should always start a quiz (2026-10-24)
- The Practice page no longer replaces the question area with a “Suggested next” lesson card when the learner presses “Pick for me.”
- Added `force_practice` to the practice endpoint. If the learning planner recommends a lesson, auto-pick uses that topic but creates a practice question instead.
- Added a frontend fallback for older backend responses and bumped the JS asset version to avoid stale browser cache.
- The Progress page may still show a recommendation as an optional next step; it does not impose a fixed order.

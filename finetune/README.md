# Fine-tuning OSLLM

This folder turns OSLLM from "Qwen3 + a system prompt" into a model trained on the Operating
Systems course itself, using QLoRA (4-bit base model + small LoRA adapters).

## 1. Check the engine and build the dataset (laptop, seconds)
```bash
bash run.sh dataset
```
This runs `verify_engine.py`, `verify_solvers.py` and `build_dataset.py`:
- **verify_engine.py**: every training answer comes from `core/scheduler_engine.py`, so the
  engine is checked first. It must agree with an independent tick-by-tick simulator on 5,000
  random problems (all six algorithms, with arrivals, idle gaps, ties, preemption and
  priorities), and every schedule must satisfy basic invariants. If OSTEP's `scheduler.py` is
  passed with `--ostep`, it is also compared against the textbook authors' own simulator.
- **verify_solvers.py**: the other numericals come from `core/os_solvers.py`, which must agree with
  separate reference implementations on 2,000 random problems per check: FIFO and LRU, OPT against
  an exhaustive minimum, Banker's and detection against every permutation, the six disk algorithms
  against closed-form totals, and the four memory-allocation strategies.
- **build_dataset.py** writes `data/train.jsonl`, `data/val.jsonl`, `data/test.jsonl`,
  `data/eval_numericals.json`, `data/eval_tasks.json` and `data/stats.json`.

| Type | Train | What it teaches |
|---|---|---|
| solve | 3,000 | full worked solutions for FCFS, SJF, SRTF, both Priority kinds and RR (500 each): decision-by-decision steps, Gantt chart, table with the working, averages |
| mistake | 650 | diagnosing a student's answer: TAT = CT, WT = CT − BT, response time used as waiting time, or a correct answer |
| quick | 500 | single calculations: TAT/WT/RT of one process, preempted processes, throughput, utilisation, exponential averaging, RR waiting bound, rate-monotonic test |
| compare | 450 | the same processes under 2–3 algorithms, with the reason they differ |
| quantum | 180 | Round Robin under several quanta |
| task | 1,920 | Banker's safety, resource request and deadlock detection; FIFO, LRU and OPT; the six disk algorithms; first, best, worst and next fit (120 each), step by step |
| task_compare | 300 | the same reference string, request queue or holes under 2–3 algorithms, with a table and why they differ |
| concept | 615 | 115 hand-written concept answers across all nine units (`concept_qa.py`, `concept_qa_syllabus.py`) in 1–3 phrasings each, repeated 3× |
| mood | 700 | any of the above asked in a confused, anxious, frustrated, formal or rushed way, answered in the matching style |
| refusal | 22 | questions outside Operating Systems declined politely |

Questions vary in wording, layout (inline, table, lists, sentences), units and what is asked.
The test split (180 CPU numericals, 128 other numericals, 15 concepts, 6 refusals) uses problems
that never appear in training or validation; the build reports the overlap (it is 0).

`python finetune/build_dataset.py --scale 2` doubles the generated examples.

## 2. Train on Google Colab (free T4 GPU)
Open `OSLLM_finetune.ipynb` in Colab, set the runtime to T4 GPU, upload `data/train.jsonl` and
`data/val.jsonl`, and run all cells. It trains for one epoch and downloads `osllm-ft.gguf`.
The 8B model takes roughly 1–2 hours on a T4; the 4B model about half that.

## 3. Use it
Put `osllm-ft.gguf` in this folder and run `bash run.sh`. The launcher imports it into Ollama
as `osllm-ft` (using `Modelfile.finetuned`) and the app switches to it.

## 4. Measure the difference
```bash
bash run.sh eval osllm        # base model
bash run.sh eval osllm-ft     # fine-tuned model
```
Each run scores 60 held-out CPU numericals (10 per algorithm), about 20 numericals from the other
solvers (page faults, total head movement, Banker's safe or unsafe), the refusals, and saves every
answer in `results/` for reading the concept answers.

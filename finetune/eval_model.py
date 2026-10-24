"""
Score a model on the held-out test split (problems never seen in training).

  numericals : average TAT and WT must match the engine's answer (within 0.01)
  tasks      : page faults, total head movement, and Banker's safe/unsafe must match the solvers' answer
  refusals   : off-topic questions must be declined
  concepts   : answers must not be empty (printed for a manual read)

Run (Ollama must be running):
  python finetune/eval_model.py --model osllm      --n 60    # base model
  python finetune/eval_model.py --model osllm-ft   --n 60    # fine-tuned model
Results are saved in finetune/results/.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from core.llm import LLM, LLMError  # noqa: E402
from build_dataset import SYSTEM  # noqa: E402

NUM = r"(-?\d+(?:\.\d+)?)"


def last_number_on_line(text: str, pattern: str):
    found = None
    for line in text.splitlines():
        if re.search(pattern, line, re.I):
            nums = re.findall(NUM, line.replace("**", ""))
            if nums:
                found = float(nums[-1])
    return found


def extract(text: str):
    tat = last_number_on_line(text, r"average\s+(tat|turnaround)|avg\.?\s+tat")
    wt = last_number_on_line(text, r"average\s+(wt|waiting)|avg\.?\s+wt")
    return tat, wt


def refused(text: str) -> bool:
    return bool(re.search(r"(outside what I teach|only (teach|cover|answer).{0,40}operating systems|not (about|related "
                          r"to) operating systems|outside (the )?operating systems)", text, re.I))


def task_pass(it: dict, text: str) -> tuple[bool, object]:
    if "faults" in it:
        got = last_number_on_line(text, r"page faults|number of faults")
        return got is not None and int(got) == it["faults"], got
    if "total" in it:
        got = last_number_on_line(text, r"total (head movement|seek|distance)")
        return got is not None and int(got) == it["total"], got
    tail = text[-600:].lower()
    got = "unsafe" if re.search(r"\bunsafe\b|not (in )?a safe|not safe", tail) else "safe" if "safe" in tail else None
    return got == ("safe" if it["safe"] else "unsafe"), got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="osllm")
    ap.add_argument("--n", type=int, default=60, help="number of test numericals (max 180)")
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()

    llm = LLM(args.model)
    ok, msg = llm.health()
    if not ok:
        sys.exit(msg)
    items = json.loads((HERE / "data" / "eval_numericals.json").read_text(encoding="utf-8"))
    rng = random.Random(args.seed)
    by_algo: dict[str, list] = {}
    for it in items:
        by_algo.setdefault(it["algorithm"], []).append(it)
    per = max(1, args.n // len(by_algo))
    chosen = [x for a in by_algo for x in rng.sample(by_algo[a], min(per, len(by_algo[a])))]
    test = [json.loads(l) for l in open(HERE / "data" / "test.jsonl", encoding="utf-8")]
    refusals = [t for t in test if t["kind"] == "refusal"]
    concepts = [t for t in test if t["kind"] == "concept"]

    log, score = [], {}
    t0 = time.time()
    print(f"Evaluating {args.model} on {len(chosen)} numericals, {len(refusals)} refusals, {len(concepts)} concepts")
    for i, it in enumerate(chosen, 1):
        try:
            out = llm.chat(SYSTEM, it["question"], temperature=0.0)
        except LLMError as e:
            out = f"ERROR {e}"
        tat, wt = extract(out)
        good = tat is not None and wt is not None and abs(tat - it["avg_tat"]) <= 0.01 and abs(wt - it["avg_wt"]) <= 0.01
        s = score.setdefault(it["algorithm"], [0, 0])
        s[0] += good
        s[1] += 1
        print(f"[{i}/{len(chosen)}] {it['algorithm']:12s} {'PASS' if good else 'FAIL'}  expected "
              f"{it['avg_tat']}/{it['avg_wt']}  got {tat}/{wt}", flush=True)
        log.append({"type": "numerical", **it, "got_tat": tat, "got_wt": wt, "pass": good, "answer": out})
    task_items = json.loads((HERE / "data" / "eval_tasks.json").read_text(encoding="utf-8"))
    by_task: dict[str, list] = {}
    for it in task_items:
        by_task.setdefault(it["algorithm"], []).append(it)
    per_t = max(1, args.n // 3 // max(1, len(by_task)))
    chosen_t = [x for a in by_task for x in rng.sample(by_task[a], min(per_t, len(by_task[a])))]
    for i, it in enumerate(chosen_t, 1):
        try:
            out = llm.chat(SYSTEM, it["question"], temperature=0.0)
        except LLMError as e:
            out = f"ERROR {e}"
        good, got = task_pass(it, out)
        s = score.setdefault(it["algorithm"], [0, 0])
        s[0] += good
        s[1] += 1
        print(f"[task {i}/{len(chosen_t)}] {it['algorithm']:12s} {'PASS' if good else 'FAIL'}  got {got}", flush=True)
        log.append({"type": "task", **it, "got": got, "pass": good, "answer": out})
    ref_ok = 0
    for t in refusals:
        out = llm.chat(SYSTEM, t["messages"][1]["content"], temperature=0.0)
        ref_ok += refused(out)
        log.append({"type": "refusal", "question": t["messages"][1]["content"], "pass": refused(out), "answer": out})
    for t in concepts:
        out = llm.chat(SYSTEM, t["messages"][1]["content"], temperature=0.0)
        log.append({"type": "concept", "question": t["messages"][1]["content"], "reference": t["messages"][2]["content"],
                    "answer": out})

    total = sum(v[0] for v in score.values())
    n = sum(v[1] for v in score.values())
    print("\n" + "=" * 52)
    print(f" {args.model}: numerical accuracy by algorithm (CPU scheduling, then the other solvers)")
    for a, (k, m) in score.items():
        print(f"   {a:12s} {k:3d} / {m:<3d} {k / m:6.0%}")
    print(f"   {'ALL':12s} {total:3d} / {n:<3d} {total / max(1, n):6.0%}")
    print(f" refusals correct: {ref_ok} / {len(refusals)}")
    print(f" time: {(time.time() - t0) / 60:.1f} min")
    print("=" * 52)
    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)
    path = out_dir / f"eval_{args.model.replace(':', '_')}_{datetime.now():%Y%m%d_%H%M}.json"
    path.write_text(json.dumps({"model": args.model, "numerical": score, "refusals": [ref_ok, len(refusals)],
                                "log": log}, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {path} (concept answers are in the log for a manual read)")


if __name__ == "__main__":
    main()

"""Print statistics about the knowledge base after extraction and chunking.

Run:  python chunk_stats.py
"""
import re
import statistics as st

import config
from core.rag import load_documents, split_text

TOPICS = {
    "FCFS": r"fcfs|(?<!sched_)fifo|first-come|first come",
    "SJF": r"\bsjf\b|shortest job",
    "SRTF": r"srtf|stcf|shortest remaining|shortest time-to-completion",
    "Priority": r"priorit",
    "Round Robin": r"round robin|round-robin|quantum",
    "Multilevel queues": r"multilevel|multi-level|mlfq",
    "Real-time": r"real-time|deadline|rate-monotonic|\bedf\b",
    "Criteria / formulas": r"turnaround|waiting time",
    "System calls / interrupts": r"system call|interrupt|\btrap\b|kernel mode",
    "Processes / threads / IPC": r"\bfork\(|process control block|\bpcb\b|thread|message passing|shared memory|pipe",
    "Synchronization": r"semaphore|mutex|critical section|peterson|race condition|monitor",
    "Deadlocks / Banker's": r"deadlock|banker|safe sequence|safe state",
    "Memory / paging": r"\bpaging\b|page table|\btlb\b|segmentation|first fit|best fit|worst fit|fragmentation",
    "Virtual memory": r"page fault|page replacement|\blru\b|belady|thrashing|working set|demand paging",
    "File systems / disk": r"inode|file allocation|directory|sstf|c-scan|\bscan\b|head movement|cylinder",
    "Linux commands": r"chmod|\bgrep\b|\bls -l|\bps aux|\bkill\b",
}


def main():
    docs = load_documents(config.KNOWLEDGE_DIR)
    chunks = []
    print(f"{'source':58s} {'words':>6s} {'chunks':>6s}")
    for text, source, page, url, origin in docs:
        pieces = [c for c in split_text(text) if len(c.strip()) >= 60]
        chunks += [(origin, source, c) for c in pieces]
        print(f"{source[:58]:58s} {len(text.split()):6d} {len(pieces):6d}")

    lengths = [len(c) for _, _, c in chunks]
    over = sum(n > config.CHUNK_SIZE for n in lengths)
    no_end = sum(1 for _, _, c in chunks if not re.search(r"[.?!:)\]\"]\s*$", c.strip()))
    biggest = max({s for _, s, _ in chunks}, key=lambda s: sum(x == s for _, x, _ in chunks))
    share = sum(s == biggest for _, s, _ in chunks) / len(chunks)

    print(f"\ndocuments: {len(docs)}   chunks: {len(chunks)}   "
          f"(course notes {sum(o != 'universal' for o, _, _ in chunks)}, "
          f"universal {sum(o == 'universal' for o, _, _ in chunks)})")
    print(f"chunk length: min {min(lengths)}, mean {st.mean(lengths):.0f}, "
          f"median {st.median(lengths):.0f}, max {max(lengths)} characters")
    print(f"chunks over the {config.CHUNK_SIZE}-character limit: {over}")
    print(f"chunks not ending at a sentence end: {no_end}")
    print(f"largest single source: {share:.0%} of all chunks ({biggest[:40]})")
    print("\nchunks mentioning each topic (all / course notes):")
    for name, pattern in TOPICS.items():
        all_n = sum(1 for _, _, c in chunks if re.search(pattern, c, re.I))
        notes_n = sum(1 for o, _, c in chunks if o != "universal" and re.search(pattern, c, re.I))
        print(f"  {name:27s} {all_n:4d} / {notes_n}")


if __name__ == "__main__":
    main()

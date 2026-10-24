"""Keeps OSLLM on the Operating Systems course: every chat question is checked before it is answered."""
from __future__ import annotations

import re

from core.llm import LLM, LLMError

# Words that only appear in Operating Systems questions -> answer directly
_STRONG = re.compile(
    # scheduling
    r"schedul|gantt|fcfs|first[- ]come|\bsjf\b|shortest\s+job|srtf|shortest\s+remaining|round\s*robin|"
    r"\brr\b|quantum|time\s+slice|preempt|dispatch|context\s+switch|waiting\s+time|turnaround|"
    r"response\s+time|throughput|cpu\s+utili|starvation|\baging\b|ageing|convoy|multilevel|feedback\s+queue|"
    r"ready\s+queue|rate[- ]monotonic|earliest\s+deadline|\bedf\b|affinity|load\s+balanc|\bcfs\b|"
    r"burst|arrival\s+time|completion\s+time|\btat\b|cpu[- ]bound|i/o[- ]bound|\bp\s*\d+\b|"
    # structure, processes, threads, IPC
    r"operating\s+system|\bkernel\b|microkernel|monolithic|system\s+calls?|\binterrupts?\b|\btrap\b|dual[- ]mode|"
    r"user\s+mode|\bpcb\b|process\s+(control|state|creation|termination)|\bfork\b|\bexec\b|zombie|orphan|"
    r"thread|multithread|pthread|\bipc\b|inter[- ]?process|shared\s+memory|message\s+passing|\bpipes?\b|"
    # synchronization, deadlock
    r"race\s+condition|critical\s+section|mutual\s+exclusion|peterson|mutex|semaphore|spinlock|monitor|"
    r"producer[- ]consumer|bounded[- ]buffer|readers[- ]writers|dining\s+philosophers|deadlock|banker|"
    r"safe\s+(state|sequence)|resource[- ]allocation\s+graph|wait[- ]for\s+graph|circular\s+wait|hold\s+and\s+wait|"
    # memory, virtual memory
    r"\bpaging\b|page\s+(table|fault|replacement|frame|size)|\bframes?\b|\btlb\b|segmentation|virtual\s+memory|"
    r"demand\s+paging|\blru\b|belady|thrashing|working\s+set|fragmentation|first[- ]fit|best[- ]fit|worst[- ]fit|"
    r"next[- ]fit|address\s+(binding|translation)|logical\s+address|physical\s+address|\bmmu\b|swapping|"
    r"relocation\s+register|copy[- ]on[- ]write|"
    # storage, files, Linux
    r"file\s+system|inode|directory\s+structure|file\s+allocation|\bfat\b|disk\s+schedul|cylinder|\bsstf\b|"
    r"c[- ]?scan|c[- ]?look|seek\s+time|rotational\s+latency|\braid\b|\bchmod\b|\bgrep\b|\bls\b\s|linux|unix|"
    r"\bshell\b|bash|terminal\s+command|\bps\b\s|\bkill\b", re.I)
# Words that may or may not be about OS -> ask the LLM to decide
_WEAK = re.compile(r"process|cpu|memory|disk|file|queue|priority|lock|resource|\bos\b|algorithm|command|"
                   r"cache|buffer|signal|device|driver|boot", re.I)
# Short follow-ups that only make sense in an ongoing conversation
_FOLLOW_UP = re.compile(
    r"^(why|how|how so|again|more|elaborate|explain( it| that| this)?( again| more| simply| better)?|"
    r"(give |show )?(me )?(another|one more) example|simpler|in simple words|i (don'?t|do not) understand|"
    r"ok|okay|thanks|thank you|got it|continue|go on|next)[\s?.!]*$", re.I)

CLASSIFY = """Is this question about Operating Systems as taught in a university OS course (OS structure,
system calls, processes, threads, IPC, CPU scheduling, synchronization, deadlocks, memory management,
paging, virtual memory, file systems, disk scheduling, Linux commands)?
Return JSON only: {{"on_topic": true/false, "subject": "the subject it is about, e.g. Computer Networks, or null"}}

{previous}Question: {question}"""

COVERS = ("OS structure and system calls, processes, threads and IPC, CPU scheduling, process "
          "synchronization, deadlocks (Banker's algorithm), memory management and paging, virtual memory "
          "and page replacement, file systems and disk scheduling, and Linux commands")
SUGGESTIONS = ["Solve Banker's algorithm for a safe sequence with an example",
               "Compare FIFO, LRU and Optimal page replacement",
               "Explain semaphores with the producer-consumer problem"]


def off_topic_message(subject: str | None = None) -> str:
    msg = "**That's outside what I teach.** "
    if subject:
        msg += f"*{subject}* is a different subject. "
    msg += f"I'm OSLLM and I only teach **Operating Systems**: {COVERS}.\n\nTry asking:\n"
    msg += "\n".join(f"- *{s}*" for s in SUGGESTIONS)
    return msg


def check_topic(question: str, llm: LLM, history: list[dict] | None = None) -> tuple[bool, str]:
    """Return (on_topic, message_if_off_topic)."""
    q = question.strip()
    if _STRONG.search(q + " "):
        return True, ""
    if history and _FOLLOW_UP.match(q):
        return True, ""                      # pure follow-up like "why?" or "explain again"
    last_user = next((m["content"] for m in reversed(history or []) if m.get("role") == "user"), "")
    previous = (f"(The student's previous question was: \"{last_user}\". Treat the new question as on topic "
                f"if it continues that Operating Systems discussion.)\n") if last_user else ""
    try:
        data = llm.chat_json("You classify questions. Reply with JSON only.",
                             CLASSIFY.format(question=q, previous=previous), temperature=0.0)
        if data.get("on_topic") is True:
            return True, ""
        subject = data.get("subject")
        subject = subject if isinstance(subject, str) and subject.strip().lower() not in ("", "null", "none") else None
        return False, off_topic_message(subject)
    except LLMError:
        # LLM unavailable: allow questions that look OS-related, block the rest
        return (True, "") if _WEAK.search(q) else (False, off_topic_message())

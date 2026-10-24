"""Map a free-text request ("quiz me on paging") to the closest syllabus topic."""
from __future__ import annotations

import re

import config
from core import problems
from core.topic_outlines import OUTLINES

_DOMAIN_TOPIC = {"bankers": "Deadlock Prevention & Avoidance (Banker's)", "page": "Page Replacement",
                 "disk": "Disk Scheduling", "alloc": "Contiguous Memory Allocation"}
_ALIASES = [  # (pattern, topic) checked first
    (r"mlfq|multi-?level", "Multilevel Queue & Feedback Queue"),
    (r"virtual\s+memory|demand\s+paging|page\s+fault\s+(rate|service|handling)|copy[- ]on[- ]write", "Demand Paging"),
    (r"\btlb\b|page\s+table|segmentation|effective\s+access", "Paging & Segmentation"),
    (r"real[- ]time|rate[- ]monotonic|\bedf\b|multiprocessor|affinity", "Multiprocessor & Real-Time Scheduling"),
    (r"peterson|critical\s+section|race\s+condition", "Critical Section & Peterson's Solution"),
    (r"system\s+calls?|interrupts?|\btrap\b", "System Calls & Interrupts"),
    (r"\bipc\b|inter[- ]?process|message\s+passing|shared\s+memory|pipes?\b|producer", "Inter-process Communication"),
    (r"kernel|microkernel|monolithic|os\s+structure|dual[- ]mode", "OS Introduction & Structure"),
    (r"detect(ion)?|recovery|wait[- ]for", "Deadlock Detection & Recovery"),
]
_STOP = set("a an and the of in on to for with is are what how why explain me my quiz viva test ask question "
            "questions give some about please".split())


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z][a-z'-]+", text.lower()) if w not in _STOP and len(w) > 1}


def topic_for(text: str) -> str | None:
    for pat, topic in _ALIASES:
        if re.search(pat, text, re.I):
            return topic
    dom = problems.detect_domain(text)
    if dom:
        return _DOMAIN_TOPIC[dom]
    words = _words(text)
    if not words:
        return None
    best, score = None, 0.0
    for t in config.TOPICS:
        name = _words(t)
        query = _words(OUTLINES[t]["query"])
        s = 3 * len(words & name) + len(words & query)
        s += 2 * sum(1 for w in words if len(w) > 3 and any(n.startswith(w[:5]) for n in name))
        if s > score:
            best, score = t, s
    return best if score >= 2 else None

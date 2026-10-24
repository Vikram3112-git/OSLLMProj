"""
Emotion and tone sensing.

Reads each message (and the recent conversation) and works out:
  * mood      - how the student seems to feel: confused, frustrated, anxious, rushed, tired,
                curious, happy or neutral
  * tone      - how they write: casual or formal
  * intensity - how strongly the mood shows (0-1)
  * social    - whether the message is mainly a greeting / feeling / thanks rather than a question

It is rule-based on purpose: it runs instantly, needs no extra model call, and every
decision can be explained ("you wrote 'I still don't get it' twice"). The result is
turned into a style instruction that changes how the LLM answers, and a short
plain-language line the interface shows the student.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict

# (pattern, weight). Patterns are matched case-insensitively against the message.
CUES: dict[str, list[tuple[str, float]]] = {
    "confused": [
        (r"\b(confus\w*|lost|unclear|makes? no sense|doesn'?t make sense)\b", 1.0),
        (r"\b(i )?(do ?n[o']?t|dont|didn'?t|did not|can'?t|cannot) (get|understand|follow|see why)\b", 1.2),
        (r"\b(what does (that|this|it) mean|what do you mean|how come|huh|wait what)\b", 0.9),
        (r"\b(still|again) (not|no|confused|don'?t)\b", 0.8),
        (r"\b(explain (it )?(again|simply|in simple)|simpler|in simple (words|terms)|eli5)\b", 0.8),
        (r"\?\s*\?", 0.6),
        (r"\b(samajh nahi|samjha nahi|puriyala|puriyaladhu|ardham kaledu)\b", 1.2),
    ],
    "frustrated": [
        (r"\b(ugh+|argh+|uff+|wtf|ffs|damn|annoy\w*|irritat\w*|fed up|sick of|hate)\b", 1.2),
        (r"\b(not working|still wrong|wrong again|useless|stupid|nonsense|waste)\b", 1.0),
        (r"\b(i give up|giving up|this is (so )?hard|too hard|impossible)\b", 1.1),
        (r"!{2,}", 0.6),
        (r"\b(why (is|does) (this|it) (keep|always))\b", 0.8),
    ],
    "anxious": [
        (r"\b(exam|test|cat ?[12]?|fat|viva|quiz|mid ?sem|end ?sem|finals?)\b.{0,25}\b(tomorrow|today|tonight|"
         r"in \d+ (hours?|days?)|soon|next week|morning)\b", 1.3),
        (r"\b(tomorrow|tonight|in \d+ (hours?|days?))\b.{0,25}\b(exam|test|cat|fat|viva|quiz)\b", 1.3),
        (r"\b(nervous|worried|worry|scared|afraid|panic\w*|stress\w*|tense|anxious|anxiety|fail(ing)?|"
         r"deadline)\b", 1.1),
        (r"\b(last minute|no time|running out of time)\b", 0.9),
    ],
    "rushed": [
        (r"\b(quick(ly)?|fast|asap|hurry|in short|briefly|brief|short answer|one line|tl;?dr|just tell|"
         r"only (the )?(answer|formula)|straight to the point)\b", 1.1),
        (r"\b(in \d+ (words|lines|points))\b", 1.0),
    ],
    "tired": [
        (r"\b(tired|sleepy|exhausted|drained|burn(ed|t) out|so late|[1-4] ?am|bored|boring)\b", 1.1),
    ],
    "curious": [
        (r"\b(curious|interesting|wonder\w*|what if|in real (life|systems?|os)|real[- ]world|actually used|"
         r"how does linux|how do real|deeper|in depth|more detail)\b", 1.0),
        (r"\bwhy (is|does|do|would|not|can'?t)\b", 0.5),
    ],
    "happy": [
        (r"\b(thanks?|thank you|thx|ty|great|awesome|amazing|nice|cool|perfect|love (it|this)|got it|"
         r"makes sense now|understood|finally|yay)\b", 1.0),
        (r"(:\)|:D|😊|😄|🙂|🔥|👍|🙏|❤️)", 0.8),
    ],
}

CASUAL = re.compile(r"\b(bro|bruh|dude|da|machan|macha|yaar|yr|pls|plz|u|ur|r|gonna|wanna|gotta|lol|lmao|"
                    r"idk|tbh|ok+|okie|hey+|yo|sup|hmm+|ya|yeah|yep|nah|kinda|sorta)\b", re.I)
FORMAL = re.compile(r"\b(kindly|could you please|would you|i would like|please explain|i request|"
                    r"elaborate on|furthermore|therefore|regarding|dear|sir|madam)\b", re.I)
GREETING = re.compile(r"^\s*(hi+|hello+|hey+|yo|good (morning|afternoon|evening|night)|namaste|vanakkam|"
                      r"sup|hola)\b[\s!.,]*\w{0,12}[\s!.]*$", re.I)
SCHEDULING_WORDS = re.compile(r"schedul|gantt|fcfs|sjf|srtf|round\s*robin|\brr\b|quantum|preempt|priority|"
                              r"waiting|turnaround|burst|arrival|process|cpu|starvation|convoy|queue", re.I)

LABELS = {
    "confused": "a bit lost", "frustrated": "frustrated", "anxious": "worried about time",
    "rushed": "in a hurry", "tired": "tired", "curious": "curious", "happy": "in a good mood",
    "neutral": "focused",
}

ADAPTATION = {
    "confused": "slowing down with simpler words and one small example",
    "frustrated": "trying a different explanation and keeping it short",
    "anxious": "keeping it calm and exam-focused",
    "rushed": "keeping it brief",
    "tired": "keeping it light and short",
    "curious": "going a little deeper",
    "happy": "keeping the momentum going",
    "neutral": "",
}


@dataclass
class Reading:
    mood: str = "neutral"
    intensity: float = 0.0
    tone: str = "neutral"                 # casual | formal | neutral
    social: bool = False                  # mainly a feeling / greeting / thanks, not a question
    cues: list[str] = field(default_factory=list)
    streak: int = 0                       # how many turns in a row this mood has shown up

    def to_dict(self) -> dict:
        d = asdict(self)
        d["label"] = LABELS[self.mood]
        d["adapting"] = ADAPTATION[self.mood]
        d["summary"] = summary(self)
        return d


def _score(text: str) -> tuple[dict[str, float], dict[str, list[str]]]:
    scores, hits = {}, {}
    for mood, rules in CUES.items():
        for pattern, weight in rules:
            for m in re.finditer(pattern, text, re.I):
                scores[mood] = scores.get(mood, 0.0) + weight
                hits.setdefault(mood, []).append(m.group(0).strip())
    caps = [w for w in re.findall(r"\b[A-Z]{3,}\b", text) if w not in {"CPU", "FCFS", "SJF", "SRTF", "TAT",
                                                                      "CT", "WT", "RT", "MLFQ", "EDF", "CFS",
                                                                      "OS", "RR", "AT", "BT", "PCB", "I/O",
                                                                      "VIT", "CAT", "FAT", "SMP", "LLM", "OSLLM"}]
    if len(caps) >= 2:
        scores["frustrated"] = scores.get("frustrated", 0.0) + 0.6
        hits.setdefault("frustrated", []).append("CAPITALS")
    return scores, hits


def read(message: str, history: list[dict] | None = None) -> Reading:
    """Sense the mood and tone of the latest message, using the conversation for context."""
    text = message.strip()
    scores, hits = _score(text)

    # carry over a little of the recent mood: confusion and stress don't vanish in one message
    prev_moods = [m.get("mood") for m in (history or []) if m.get("role") == "user" and m.get("mood")]
    for i, mood in enumerate(reversed(prev_moods[-3:])):
        if mood in ("confused", "frustrated", "anxious"):
            scores[mood] = scores.get(mood, 0.0) + 0.35 / (i + 1)

    # a "why?" in an otherwise happy message is curiosity, not confusion
    if scores.get("happy") and scores.get("confused", 0) < 1.0:
        scores.pop("confused", None)
    # repeated confusion becomes frustration
    if prev_moods[-2:] == ["confused", "confused"] and scores.get("confused", 0) >= 1.0:
        scores["frustrated"] = scores.get("frustrated", 0.0) + 0.7

    mood, best = "neutral", 0.0
    order = ["frustrated", "anxious", "confused", "tired", "rushed", "curious", "happy"]  # tie priority
    for m in order:
        if scores.get(m, 0.0) > best + 1e-9:
            mood, best = m, scores[m]
    if best < 0.75:
        mood = "neutral"

    casual = len(CASUAL.findall(text)) + (0.5 if text and text == text.lower() and len(text) > 3 else 0)
    casual += 0.5 if re.search(r"(😂|🤣|😅|😭|lol|haha)", text, re.I) else 0
    formal = len(FORMAL.findall(text)) * 2.0
    tone = "casual" if casual >= 1 and casual > formal else "formal" if formal >= 2 and formal > casual else "neutral"

    is_question = "?" in text or bool(re.search(r"\b(what|why|how|when|which|who|where|explain|solve|compare|"
                                               r"give me|show me|tell me|teach|find|calculate|draw|define|write)\b",
                                               text, re.I))
    social = bool(GREETING.match(text)) or (
        mood in ("happy", "anxious", "tired", "frustrated") and not SCHEDULING_WORDS.search(text)
        and not is_question and len(text.split()) <= 25)

    streak = 1
    for m in reversed(prev_moods):
        if m == mood and mood != "neutral":
            streak += 1
        else:
            break

    return Reading(mood=mood, intensity=round(min(1.0, best / 2.5), 2), tone=tone, social=social,
                   cues=hits.get(mood, [])[:3], streak=streak if mood != "neutral" else 0)


# -------------------------------------------------------------- style for the LLM
MOOD_STYLE = {
    "confused": ("Use a patient, step-by-step explanation. Start with the core idea in plain language, define any "
                 "necessary jargon, and use one small example. Do not announce or label the student's mood."),
    "frustrated": ("Be calm and direct, without excessive sympathy. Try a different explanation from the previous "
                   "turn, make the key idea concrete, and avoid repeating what already failed. Do not label the mood."),
    "anxious": ("Use a calm, focused tone. Prioritize the exam-relevant rule, formulas, a compact worked example, "
                "and the most important examiner mistake. Do not make assumptions or announce the student's mood."),
    "rushed": ("Lead with the direct answer and be concise, but do not omit essential steps or correctness. Include "
               "only the most useful example or formula. Do not label the mood."),
    "tired": ("Use a friendly, clear tone. Break the explanation into manageable chunks and avoid unnecessary detail, "
              "while still answering the question completely. Do not label the mood."),
    "curious": ("Answer fully, then add directly relevant depth such as real OS behavior, trade-offs, or a useful "
                "edge case. Avoid tangents and unrelated facts."),
    "happy": ("Keep a friendly, encouraging tone while focusing on the substance. Offer a harder follow-up only when "
              "it naturally fits the answer."),
    "neutral": "",
}
TONE_STYLE = {
    "casual": ("Match their casual tone: friendly and relaxed, like a helpful senior explaining to a junior. "
               "Plain words, short sentences; at most one emoji in the whole reply, or none."),
    "formal": "Match their formal tone: clear, polite and professional. No slang or emoji.",
    "neutral": "",
}


def style_instruction(r: Reading) -> str:
    parts = [p for p in (MOOD_STYLE[r.mood], TONE_STYLE[r.tone]) if p]
    if r.mood in ("confused", "frustrated") and r.streak >= 2:
        parts.append(f"This is turn {r.streak} in a row where the student feels this way, so the previous "
                     "explanation did not work: use a completely different approach (a new analogy, or a "
                     "worked example instead of theory).")
    if not parts:
        return ""
    return "HOW TO ANSWER THIS STUDENT RIGHT NOW (this overrides the default structure):\n- " + "\n- ".join(parts)


def summary(r: Reading) -> str:
    """One plain sentence for the interface, e.g. 'You sound a bit lost, so I'm slowing down...'"""
    if r.mood == "neutral":
        return ""
    s = f"You sound {LABELS[r.mood]}, so I'm {ADAPTATION[r.mood]}."
    if r.mood in ("confused", "frustrated") and r.streak >= 2:
        s = f"Still {LABELS[r.mood]}? Let me try a completely different way."
    return s

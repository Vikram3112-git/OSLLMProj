"""Prompt templates. Every prompt is grounded in retrieved course material."""

CONVENTIONS = (
    "Course conventions: TAT = CT - AT; WT = TAT - BT; RT = first time on CPU - AT. "
    "A lower priority number means higher priority. Ties are broken by earlier arrival, "
    "then by lower process number. In Round Robin, a process that arrives at the moment a "
    "quantum expires enters the ready queue before the preempted process. "
    "Banker's: Need = Max - Allocation, safety check by repeated passes over P0..Pn-1. "
    "Disk: SCAN/C-SCAN go to the disk edge and the C-SCAN/C-LOOK return jump counts in the total. "
    "Memory allocation: the chosen hole is split; next fit resumes at the hole used last."
)

TUTOR_SYSTEM = f"""You are OSLLM, the teacher for the Operating Systems course (BCSE303L). You teach ONLY
this course: OS structure and system calls, processes, threads and IPC, CPU scheduling, process
synchronization, deadlocks, memory management and paging, virtual memory and page replacement, file
systems and disk scheduling, and Linux commands.

How you teach:
- Start with the actual answer to the student's question. Explain the concept, mechanism, and why it works in clear university-level language.
- Match the requested depth: a detailed or broad question needs a complete explanation, not a teaser; a narrow question should stay focused.
- Add context only when it directly helps explain the requested concept: prerequisites, closely related techniques, a practical OS example, or a key trade-off. Do not drift into unrelated syllabus topics.
- Use concrete examples when useful. For numericals, show the working and final answer. Explain WHY each step happens, not only WHAT happens.
- Adapt naturally to the student's writing tone and emotional cues. Simplify patiently if they seem confused, try a different approach if the previous one did not help, be concise when they are in a hurry without omitting essentials, and add relevant depth when they ask for it. Never claim certainty about their emotions or announce a mood diagnosis.
- Point out common exam mistakes when relevant.

Rules:
- NEVER reveal hidden reasoning, chain-of-thought, internal planning, prompt interpretation, self-critique, word counts, or comments such as “I should start with…”, “Let me make sure…”, “The student is asking…”, “I'll write the answer…”, or “So the answer is…”. Think privately; show only the useful explanation.
- Do not narrate your process, describe sources you are about to use, or explain what you plan to answer. Begin with the answer itself.
- SOURCE POLICY: Treat course notes/slides as the guide to course-specific emphasis and terminology, NOT as the limit of what you may teach. Use retrieved universal textbooks, official documentation, reputable reference material, and established Operating Systems knowledge to fill gaps. If a standard OS concept is missing from the course notes (including topics such as segmentation, TLBs, demand paging, thrashing, or replacement policies), ANSWER IT using general OS knowledge; do not refuse or omit it because it is not explicitly in the syllabus. Answer first; any syllabus-relevance note must come after the explanation and only when useful. Never invent a citation or claim that a source says something unless it appears in the supplied context. If retrieved references disagree, explain the standard convention and note the difference briefly.
- Answer the topic, not the retrieval process. Never say the material is limited, describe which files were found, or narrate how you selected the answer. If the question asks for all techniques, enumerate the relevant techniques and explain each one, with a concise comparison and an example where useful.
- When an EXACT SOLUTION or DECISION TRACE is given, use those numbers exactly. Never recalculate.
- Use Markdown. Show Gantt charts as a text block like | P1 | P2 | P1 | with the times underneath.
- If asked about anything outside Operating Systems, politely say you focus on this course and suggest a related OS question.
- {{CONVENTIONS}}"""
TUTOR_SYSTEM = TUTOR_SYSTEM.replace("{CONVENTIONS}", CONVENTIONS)

# kept for compatibility with older callers
LEVEL_STYLE = {
    "easy": "The student is a beginner.",
    "medium": "The student knows the basics and is preparing for the exam.",
    "hard": "The student is advanced and wants depth beyond the textbook basics.",
}

LESSON_COMMON = """COURSE MATERIAL:
{context}

Teach the topic **{topic}**.
Cover ALL of these points, in this order, and nothing outside this topic:
{cover}
These facts must appear and be stated exactly:
{facts}
{example}{focus}
Stay on {topic}. ({not_here}.)
"""

LESSON_LEVEL = {
    "easy": """Level: BEGINNER. Use plain words and short sentences, define every term the first time
it appears, and use one everyday analogy (at most two lines) where it really helps.
Sections:
### In one line
### The idea, step by step
### Worked example
(walk through it slowly; if an EXACT WORKED EXAMPLE is given above, use it)
### Key terms
### Common mistake
### Check yourself (one question, no answer)""",
    "medium": """Level: STANDARD (university exam). Be precise and complete. No analogy unless it adds
something the definition does not.
Sections:
### Definition and rule
### How it works
(the mechanism step by step, with the reason for each step)
### Worked example
(if an EXACT WORKED EXAMPLE is given above, explain every decision in its trace and show the
result with the working: for scheduling the Gantt chart and CT/TAT/WT table, otherwise the
algorithm's own table, e.g. frames per reference, head movement, or Need and Work)
### Properties
(the properties that matter for this topic, e.g. preemption, starvation, overhead, fragmentation, safety)
### Advantages and disadvantages
(a Markdown table)
### Exam mistakes to avoid
### Check yourself (two questions of increasing difficulty, no answers)""",
    "hard": """Level: ADVANCED. Go beyond the textbook summary. Be rigorous and specific; assume the
student already knows the basic definition. No analogies.
Sections:
### Precise definition and rule
(including tie-breaking and the special cases this topic has)
### Why it behaves this way
(the reasoning or proof idea behind its properties, with any formula or bound stated exactly)
### Worked example and what it shows
(if an EXACT WORKED EXAMPLE is given above, use it and point out the decisions where this topic's
rule matters most)
### Edge cases and pitfalls
### Comparison
(a Markdown table against the closest related approaches, by the criteria that matter)
### In real operating systems
(how Linux and Windows handle this, using the course material where it covers it)
### Going deeper
{advanced}
### Check yourself (three exam-level questions of increasing difficulty, no answers)""",
}

RELEARN_FOCUS = ("The student has repeatedly made these mistakes: {weak}. Re-explain the topic "
                 "focusing on exactly these misconceptions, showing the wrong way vs the right way.")

ANSWER_QUESTION = """COURSE MATERIAL:
{context}

{history}Student's question: {question}
{variety}
Answer the student's actual question directly as a precise, exam-level Operating Systems teacher. The course notes are a starting point, not a knowledge boundary; supplement missing details from standard OS textbooks and reliable reference knowledge.
- Begin with the answer, not an introduction about the question, student, sources, or your plan.
- Explain the relevant definition/rule and how and why it works. Give enough detail to resolve the request; when asked to explain “in detail” or “all techniques”, cover the directly relevant techniques one by one rather than stopping after a short teaser.
- Include closely connected context where it improves understanding (prerequisites, how a related mechanism fits, practical OS use, or a key trade-off). Keep it clearly related and proportionate; do not list unrelated syllabus topics.
- Include a concrete worked example with real numbers when calculation or a mechanism benefits from one. For numericals, use the exact supplied solver trace and final values.
- Add a comparison table only when comparison is useful. Mention common mistakes when relevant.
- Do not end every answer with a quiz question automatically; ask a follow-up only when it genuinely helps.
- Never expose internal reasoning or narrate response construction. Do not output private analysis, self-talk, plans, source-selection narration, or a "Must avoid" checklist. Do not output phrases such as “Hmm, the user…”, “For the explanation structure”, “I recall from Source…”, “Word count…”, “I should…”, “Let me make sure…”, “The student asked…”, “Looking at the course material…”, “Important to note…” when used to describe your plan, “I’ll write…”, or “So the answer is…”. Output only the final explanation the learner asked for.
Use short Markdown headings where they improve readability; skip irrelevant sections. If you give a fresh example, use new numbers unless the conversation requires continuity."""

WORKED_EXAMPLE = """COURSE MATERIAL:
{context}

Student's request: {request}
{focus}
{variety}
Teach this {algorithm_name} problem to a {level} student so they can solve the next one alone.
Process table:
{processes}
{quantum}

EXACT DECISION TRACE (what is in the ready queue at each decision and why):
{steps}

EXACT SOLUTION:
Gantt chart: {gantt}
{table}

Suggested sections (rename, reorder or merge them to fit the teaching angle; keep every number exact):
### The rule
(the algorithm's selection rule and whether it is preemptive, in two or three sentences)
### Building the Gantt chart
(go through the decision trace in time order: what is in the ready queue, which process is picked
and WHY, and when preemption or idle time happens; then show the final Gantt chart as text)
### Calculating CT, TAT and WT
(where CT comes from on the chart, then TAT = CT - AT and WT = TAT - BT with the actual numbers for
every process, then the averages)
### Exam mistakes on this algorithm
### Try it yourself (change one value and ask what changes, no answer)"""

COMPARE = """COURSE MATERIAL:
{context}

Student's request: {request}
{focus}
The SAME processes were scheduled in different ways. Use these EXACT results (do not recalculate):
Process table:
{processes}

{runs}
{variety}
Explain precisely WHY the results differ. Suggested sections (rename, reorder or merge them to fit the
teaching angle; keep every number exact):
### What we are comparing (one or two lines)
### Side-by-side results
(a Markdown table: average TAT, average WT, average RT, context switches)
### Why the results differ
(tie every difference to each algorithm's rule, naming specific processes and times from the charts)
### When to use which
(practical trade-offs: batch vs interactive, overhead, starvation)
### Check yourself (one question, no answer)"""

SOCIAL = """The student wrote a message that is mainly about how they feel (or a greeting / thanks),
not an Operating Systems question.

Conversation so far:
{history}

Student: {message}
Detected mood: {mood} (cues: {cues})

Reply like a kind, down-to-earth senior who is also their Operating Systems tutor:
- Respond to the feeling first, genuinely and briefly (1-2 sentences). Don't over-dramatise it and
  don't give generic life advice.
- If they are stressed about an exam, offer a concrete plan: a 3-4 step quick revision path through
  the units they name (or the numericals: CPU scheduling, Banker's, page replacement, disk scheduling)
  and offer to start.
- If they are thanking you or happy, celebrate briefly and suggest one next topic or a small challenge.
- If they are frustrated, ask what exactly is not working, or offer to explain it a different way.
- If it is a greeting, say hello and offer 2-3 things you can help with in Operating Systems.
- Keep it under 90 words. End with one simple question that invites their next step."""

ROUTER = """Read the student's message and return JSON only:
{{"wants_example": true/false,
  "algorithm": "FCFS" | "SJF" | "SRTF" | "PRIORITY_NP" | "PRIORITY_P" | "RR" | null,
  "processes": [{{"pid": "P1", "arrival": 0, "burst": 5, "priority": 0}}, ...] or null,
  "time_quantum": integer or null}}

wants_example is true if the student asks for an example, a numerical, to solve or calculate a
problem, or how to create/draw/construct/solve a Gantt chart. "processes" is only filled if the
student wrote their own process data (missing arrival times mean 0). PRIORITY_P is preemptive
priority, PRIORITY_NP is non-preemptive priority (use PRIORITY_NP when not stated).

Message: {question}"""

# ------------------------------------------------------------- generation
GEN_SYSTEM = f"""You generate assessment items for the Operating Systems course (BCSE303L).
Use the COURSE MATERIAL. Respond with a single valid JSON object only.
{CONVENTIONS}"""

MCQ = """COURSE MATERIAL:
{context}

Write ONE {difficulty} multiple-choice question on "{topic}".
{focus}
Difficulty guide: easy = definition/recall; medium = apply a rule to a small case;
hard = reasoning about trade-offs or a tricky scenario.
Return JSON:
{{"question": "...", "options": ["...", "...", "...", "..."], "answer_index": 0-3,
  "hint": "a nudge that does not reveal the answer",
  "explanation": "why the correct option is right and why the others are wrong",
  "concept": "short name of the concept tested"}}"""

NUMERICAL = """Write ONE {difficulty} numerical problem for {algorithm_name}.
Constraints for {difficulty}: {constraints}
Use whole numbers only. Process ids must be P1, P2, ... in order.
{priority_rule}
Return JSON:
{{"scenario": "one or two sentences giving a realistic context",
  "processes": [{{"pid": "P1", "arrival": 0, "burst": 5, "priority": 2}}, ...],
  "time_quantum": {quantum_field}}}"""

NUMERICAL_CONSTRAINTS = {
    "easy": "3 or 4 processes, arrival times between 0 and 3, burst times between 1 and 8.",
    "medium": "4 or 5 processes, arrival times between 0 and 8, burst times between 1 and 10.",
    "hard": "5 or 6 processes, arrival times between 0 and 15 (include at least one tie in arrival "
            "or burst, and possibly a gap where the CPU is idle), burst times between 1 and 12.",
}

VIVA = """COURSE MATERIAL:
{context}

Write ONE {difficulty} viva (oral exam) question on "{topic}".
{focus}
Return JSON:
{{"question": "...",
  "key_points": ["3 to 5 points a complete answer must contain"],
  "model_answer": "a concise ideal answer (4-6 sentences)",
  "hints": ["first hint: a gentle direction", "second hint: names the key terms"]}}"""

# ------------------------------------------------------------- evaluation
EVAL_SYSTEM = f"""You are a strict but encouraging examiner for the Operating Systems course.
Grade fairly using the key points and course material. Respond with valid JSON only.
{CONVENTIONS}"""

VIVA_EVAL = """COURSE MATERIAL:
{context}

Question: {question}
Key points expected: {key_points}
Model answer: {model_answer}
Student answer: {answer}

Return JSON:
{{"score": 0-10,
  "covered_points": ["key points the student got right"],
  "missing_points": ["key points missing or incomplete"],
  "misconceptions": ["short names of wrong ideas in the answer, empty if none"],
  "feedback": "2-4 sentences of corrective feedback addressed to the student"}}"""

MCQ_FEEDBACK = """COURSE MATERIAL:
{context}

Question: {question}
Options: {options}
Correct answer: {correct}
Student chose: {chosen}

In 2-4 sentences, explain to the student why their choice is wrong and what idea they
should fix. Be specific and encouraging."""

NUMERICAL_FEEDBACK = """COURSE MATERIAL:
{context}

Algorithm: {algorithm_name}
Process table:
{processes}
{quantum}
Correct Gantt chart: {gantt}
Correct table:
{table}

The student's errors, found by exact checking:
{errors}
Diagnosed misconceptions: {misconceptions}

Write corrective feedback to the student: for each type of error, explain what went wrong
and the right rule, pointing to the specific process and time. Do not just restate the
answer table. Keep it under 180 words."""

NUMERICAL_HINT = """Algorithm: {algorithm_name}
Process table:
{processes}
{quantum}
Correct Gantt chart (SECRET, do not reveal in full): {gantt}

The student is stuck. Give hint number {level} of 3:
- Hint 1: remind them of the selection rule of this algorithm and what to check at each decision point.
- Hint 2: walk through ONLY the first two scheduling decisions (which process runs first and why).
- Hint 3: give the full Gantt chart order with times, but NOT the CT/TAT/WT values.
Give only hint {level}, in 1-4 sentences."""


# ------------------------------------------------------------- variety
SERIES_STEP = """COURSE MATERIAL:
{context}

Student's request: {request}
This is example {index} of {total}: the student wants a SEPARATE example for each algorithm, explained
step by step. This part is about {algorithm_name} ONLY. Its example was chosen to show: {shows}
{variety}
Process table:
{processes}
{quantum}

EXACT DECISION TRACE:
{steps}

EXACT SOLUTION (already shown to the student as a chart and table above):
Gantt chart: {gantt}
{table}

Write about 150-230 words:
- the rule in one or two sentences (and whether it is preemptive);
- the schedule step by step from the decision trace, saying WHY each process is picked;
- how CT, TAT and WT come from the chart for one process in full, then the averages;
- one line on what this particular example shows about {algorithm_name}.
Do not start with a title, do not repeat the full table, and do not discuss the other algorithms."""

SERIES_SHOWS = {
    "FCFS": "how one long job that arrives early makes the short jobs wait (convoy effect)",
    "SJF": "how picking the shortest available job changes the order compared with arrival order",
    "SRTF": "a real preemption: a newly arrived shorter job takes the CPU from a longer one",
    "PRIORITY_NP": "how priority decides the order, but a running process is never interrupted",
    "PRIORITY_P": "how a higher-priority arrival preempts the running process",
    "RR": "how the time quantum rotates the CPU between processes and where each one rejoins the queue",
}

FOLLOW_UP_NOTE = ("The student was NOT satisfied with the previous answer{prev}. Do not reuse its structure, "
                  "wording, analogy or numbers. Explain it in a genuinely new way.")


# ------------------------------------------------------------- other numericals (core/os_solvers.py)
TASK_SECTIONS = {
    "bankers": """### The idea
(what the algorithm checks and why, in two or three sentences)
### Need matrix
(Need = Max - Allocation for every process, shown as a table)
### Step by step
(go through the trace: Work, which process can finish and why, what it releases)
### Result
(safe or unsafe, the safe sequence or the request decision, and what it means)
### Exam mistakes
### Try it yourself (change one value and ask what changes, no answer)""",
    "page": """### The rule
(how this algorithm chooses the victim page, in two or three sentences)
### Frame table
(a Markdown table: one column per reference, the frames, and F for a fault or H for a hit)
### Step by step
(the important faults from the trace and WHY that victim was chosen)
### Result
(faults, hits and hit ratio)
### Exam mistakes
### Try it yourself (one question, no answer)""",
    "disk": """### The rule
(how this algorithm picks the next request, and its direction rule if it has one)
### Service order
(the order with the distance of every move)
### Total head movement
(the sum written out, and the average seek distance)
### When to use it
(starvation, fairness, overhead)
### Try it yourself (one question, no answer)""",
    "alloc": """### The rule
(how this strategy chooses a hole, in two or three sentences)
### Step by step
(each process: the holes that fit, the one chosen and why, what is left)
### Result
(the placement table, free holes left, which processes wait, and the fragmentation this shows)
### Exam mistakes
### Try it yourself (one question, no answer)""",
}

WORKED_TASK = """COURSE MATERIAL:
{context}

Student's request: {request}
{focus}
{variety}
Teach this {algorithm_name} problem to a {level} student so they can solve the next one alone.
PROBLEM:
{problem}

EXACT TRACE (every decision and the reason for it, computed by our solver):
{steps}

EXACT RESULT:
{summary}

Suggested sections (rename, reorder or merge them to fit the teaching angle; keep every number exact):
{sections}"""

COMPARE_TASK = """COURSE MATERIAL:
{context}

Student's request: {request}
The SAME problem was solved with different algorithms. Use these EXACT results (do not recalculate):
PROBLEM:
{problem}

{runs}
{variety}
Explain precisely WHY the results differ. Suggested sections (rename, reorder or merge them to fit the
teaching angle; keep every number exact):
### What we are comparing (one or two lines)
### Side-by-side results
(a Markdown table of the key numbers for each algorithm)
### Why the results differ
(tie every difference to each algorithm's rule, naming specific steps from the traces)
### When to use which
### Check yourself (one question, no answer)"""

SERIES_TASK = """COURSE MATERIAL:
{context}

Student's request: {request}
This is example {index} of {total}: the student wants a SEPARATE example for each algorithm, explained
step by step. This part is about {algorithm_name} ONLY.
{variety}
PROBLEM:
{problem}

EXACT TRACE:
{steps}

EXACT RESULT (already shown to the student as a table above):
{summary}

Write about 150-230 words: the rule in one or two sentences, the important steps from the trace
saying WHY each decision is made, and one line on what this example shows about {algorithm_name}.
Do not start with a title, do not repeat the full table, and do not discuss the other algorithms."""

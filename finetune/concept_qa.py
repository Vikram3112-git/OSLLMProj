"""
Hand-written concept questions and answers for fine-tuning.

Each entry: (topic, [question phrasings], answer). Answers follow the course conventions
(lower priority number = higher priority; TAT = CT - AT; WT = TAT - BT; RT = first run - AT)
and were written from our course notes, OSTEP and Silberschatz.
"""

QA = [
    # ------------------------------------------------------------------ fundamentals
    ("Fundamentals", ["What is CPU scheduling?", "Explain process scheduling.", "What does the CPU scheduler do?"],
     "CPU scheduling is how the operating system decides which ready process gets the CPU next.\n\n"
     "In a multiprogrammed system several processes are in memory at once. When the running process has to wait, "
     "usually for I/O, the OS gives the CPU to another ready process instead of letting it sit idle. The short-term "
     "scheduler picks that process from the ready queue, and the dispatcher actually switches to it.\n\n"
     "The goal is to keep the CPU busy while also giving good turnaround, waiting and response times."),
    ("Fundamentals", ["Why do we need CPU scheduling?", "What is the purpose of CPU scheduling?"],
     "Without scheduling, the CPU would sit idle every time a process waited for I/O.\n\n"
     "Programs alternate between computing (CPU bursts) and waiting for devices (I/O bursts). If the OS keeps "
     "several processes in memory and switches to another ready process whenever the running one blocks, the CPU "
     "stays busy. Scheduling also decides fairness and responsiveness: who waits, for how long, and how quickly an "
     "interactive user sees a response."),
    ("Fundamentals", ["What is the CPU-I/O burst cycle?", "Explain CPU burst and I/O burst."],
     "Process execution alternates between CPU bursts, where the process computes, and I/O bursts, where it waits "
     "for a device. A process starts and ends with a CPU burst.\n\n"
     "Measurements show most CPU bursts are short and only a few are long. This is why the choice of algorithm "
     "matters: an algorithm that lets short bursts go first (like SJF) or that gives everyone short turns (like "
     "Round Robin) keeps interactive and I/O-heavy processes responsive."),
    ("Fundamentals", ["What is the difference between a CPU-bound and an I/O-bound process?",
                      "CPU-bound vs I/O-bound process?"],
     "A CPU-bound process spends most of its time computing and has a few long CPU bursts, for example a video "
     "encoder. An I/O-bound process spends most of its time waiting for I/O and has many short CPU bursts, for "
     "example a text editor.\n\n"
     "A good scheduler mixes both: giving the CPU quickly to I/O-bound processes keeps the devices busy, while "
     "CPU-bound processes use the remaining CPU time."),
    ("Fundamentals", ["What are the states of a process?", "Explain the process state diagram."],
     "A process moves through five states:\n\n"
     "- **New**: being created.\n- **Ready**: waiting in the ready queue for the CPU.\n"
     "- **Running**: its instructions are executing on the CPU.\n"
     "- **Waiting (blocked)**: waiting for an event such as I/O completion.\n- **Terminated**: finished.\n\n"
     "The CPU scheduler only chooses among processes in the ready state. A running process can go to waiting "
     "(I/O request), back to ready (preempted by a timer interrupt), or to terminated."),
    ("Fundamentals", ["What is the ready queue?", "Which processes does the scheduler choose from?"],
     "The ready queue holds all processes that are in memory and ready to run, waiting only for the CPU. The "
     "short-term scheduler always picks the next process from this queue. It does not have to be a FIFO queue: "
     "depending on the algorithm it can be ordered by arrival, by burst length, by priority, or kept as a circular "
     "queue for Round Robin."),
    ("Fundamentals", ["What are the long-term, short-term and medium-term schedulers?",
                      "Explain the types of schedulers.", "Difference between long term and short term scheduler?"],
     "- **Long-term (job) scheduler**: decides which jobs are admitted into memory, so it controls the degree of "
     "multiprogramming. It runs rarely.\n"
     "- **Short-term (CPU) scheduler**: picks which ready process runs next on the CPU. It runs very often, every "
     "few milliseconds, so it must be fast.\n"
     "- **Medium-term scheduler**: swaps processes out of memory and later back in, to reduce the number of "
     "processes in memory or improve the mix of CPU-bound and I/O-bound jobs.\n\n"
     "The algorithms we study (FCFS, SJF, Round Robin and so on) are short-term scheduling algorithms."),
    ("Fundamentals", ["What is the degree of multiprogramming?"],
     "The degree of multiprogramming is the number of processes in memory at the same time. The long-term "
     "scheduler controls it by deciding how many jobs to admit, and the medium-term scheduler can lower it by "
     "swapping processes out. Too low wastes the CPU; too high causes heavy swapping and slows everything down."),
    ("Fundamentals", ["What is a dispatcher?", "What does the dispatcher do?", "Scheduler vs dispatcher?"],
     "The scheduler decides which process runs next; the dispatcher carries out that decision.\n\n"
     "The dispatcher switches context (saves the old process's state and loads the new one's), switches to user "
     "mode, and jumps to the right instruction in the new process. It runs on every process switch, so it must be "
     "as fast as possible."),
    ("Fundamentals", ["What is dispatch latency?"],
     "Dispatch latency is the time the dispatcher takes to stop one process and start another. It is pure "
     "overhead, because no useful work is done during it, which is why very frequent switching (for example a very "
     "small Round Robin quantum) wastes CPU time."),
    ("Fundamentals", ["What is a context switch?", "Explain context switching."],
     "A context switch is when the CPU stops running one process and starts another. The OS saves the state of the "
     "old process (registers, program counter and other information) in its PCB and loads the saved state of the "
     "new process from its PCB.\n\n"
     "Context switches are overhead: the CPU does no useful work for the user during them. That is the cost "
     "behind preemptive scheduling and small time quanta."),
    ("Fundamentals", ["When does the CPU scheduler make a decision?", "When can scheduling decisions take place?"],
     "A scheduling decision can happen when a process:\n\n"
     "1. switches from running to waiting (for example an I/O request),\n"
     "2. switches from running to ready (for example a timer interrupt),\n"
     "3. switches from waiting to ready (for example I/O completes),\n4. terminates.\n\n"
     "If decisions happen only in cases 1 and 4, scheduling is non-preemptive. If they can also happen in cases 2 "
     "and 3, it is preemptive."),
    ("Fundamentals", ["What is the difference between preemptive and non-preemptive scheduling?",
                      "Preemptive vs non-preemptive scheduling?", "Explain preemptive scheduling."],
     "In **non-preemptive** scheduling, once a process gets the CPU it keeps it until it finishes or blocks for "
     "I/O. In **preemptive** scheduling, the OS can take the CPU away, for example when a timer interrupt fires "
     "or a higher-priority process arrives.\n\n"
     "Non-preemptive is simple and has little overhead, but one long process can make everyone else wait. "
     "Preemptive gives much better response time for interactive systems, at the cost of more context switches "
     "and the need to protect shared data.\n\n"
     "FCFS, SJF and non-preemptive Priority are non-preemptive. SRTF, preemptive Priority and Round Robin are "
     "preemptive."),
    ("Fundamentals", ["What is cooperative scheduling?"],
     "Cooperative scheduling is another name for non-preemptive scheduling: a process keeps the CPU until it "
     "voluntarily gives it up by blocking, yielding or terminating. It is simple, but a single process that never "
     "yields can stall the whole system, which is why modern general-purpose OSs use preemptive scheduling."),
    # ------------------------------------------------------------------ criteria
    ("Criteria", ["What are the CPU scheduling criteria?", "List the scheduling criteria.",
                  "What criteria are used to compare scheduling algorithms?"],
     "- **CPU utilisation**: percentage of time the CPU is busy. Maximise.\n"
     "- **Throughput**: number of processes finished per unit time. Maximise.\n"
     "- **Turnaround time**: time from arrival to completion. Minimise.\n"
     "- **Waiting time**: total time spent waiting in the ready queue. Minimise.\n"
     "- **Response time**: time from arrival until the process first gets the CPU. Minimise.\n\n"
     "Usually we compare averages over all processes. For interactive systems, keeping response time low and "
     "predictable matters most."),
    ("Criteria", ["What are the formulas for turnaround time, waiting time and response time?",
                  "Give the formulas for TAT, WT and RT.", "How do you calculate waiting time?"],
     "- **Turnaround time**: TAT = CT − AT (completion time minus arrival time)\n"
     "- **Waiting time**: WT = TAT − BT (turnaround time minus burst time)\n"
     "- **Response time**: RT = (time the process first gets the CPU) − AT\n\n"
     "Averages are the sum divided by the number of processes.\n\n"
     "A common mistake is writing TAT = CT or WT = CT − BT. Those are only right when the process arrives at "
     "time 0, so always subtract the arrival time."),
    ("Criteria", ["What is turnaround time?"],
     "Turnaround time is the total time a process spends in the system, from the moment it arrives until it "
     "completes: TAT = CT − AT. It includes the time it actually runs plus all the time it waits."),
    ("Criteria", ["What is waiting time?"],
     "Waiting time is the total time a process spends in the ready queue waiting for the CPU: WT = TAT − BT. In a "
     "preemptive algorithm a process can wait several times, and this formula automatically adds all of those "
     "waits together. The scheduling algorithm directly affects only waiting time; the burst time is the same "
     "whatever algorithm is used."),
    ("Criteria", ["What is response time?", "Difference between response time and waiting time?"],
     "Response time is the time from arrival until the process first gets the CPU: RT = first start − AT.\n\n"
     "Waiting time counts every period the process spends waiting. In non-preemptive algorithms the two are "
     "equal, because a process runs once without interruption. In preemptive algorithms such as SRTF or Round "
     "Robin, waiting time is larger, because the process waits again each time it is preempted."),
    ("Criteria", ["What is throughput?", "How do you calculate throughput?"],
     "Throughput is the number of processes completed per unit of time: throughput = number of processes ÷ total "
     "time of the schedule. For example, 4 processes finishing in a 20 ms schedule give a throughput of 0.2 "
     "processes per ms."),
    ("Criteria", ["What is CPU utilisation and how is it calculated?"],
     "CPU utilisation is the fraction of time the CPU is doing useful work: utilisation = busy time ÷ total time × "
     "100%. If the Gantt chart is 20 units long and the CPU is idle for 2 of them, utilisation is 18 ÷ 20 = 90%."),
    ("Criteria", ["What is a Gantt chart in CPU scheduling?", "How do you draw a Gantt chart?"],
     "A Gantt chart is a timeline showing which process runs during each interval, with the time written at each "
     "boundary:\n\n```\n| P1 | P2 | P3 |\n0    5    8    16\n```\n\n"
     "To draw one, start at the earliest arrival, look at the processes that have arrived, apply the algorithm's "
     "rule to pick one, decide how long it runs (to completion, until preempted, or one quantum), draw that box, "
     "and repeat. If no process has arrived, draw an idle box. The completion time of a process is the right edge "
     "of its last box."),
    ("Criteria", ["How is CPU idle time shown in a Gantt chart?", "What if no process has arrived yet?"],
     "If no process is in the ready queue, the CPU is idle. Draw an IDLE box from the current time until the next "
     "arrival. Idle time is not waiting time for any process, because no process was waiting, but it does lower "
     "CPU utilisation."),
    # ------------------------------------------------------------------ FCFS
    ("FCFS", ["What is FCFS scheduling?", "Explain First Come First Served scheduling.", "How does FCFS work?"],
     "First-Come, First-Served gives the CPU to processes in the order they arrive, like a single queue at a "
     "ticket counter. It uses a FIFO queue and is non-preemptive: once a process starts, it runs until it "
     "finishes or blocks.\n\n"
     "It is the simplest algorithm and is fair in the sense of order, but the average waiting time is often long "
     "and depends heavily on the arrival order."),
    ("FCFS", ["What are the advantages and disadvantages of FCFS?"],
     "**Advantages:** very simple to implement, low overhead, and no starvation, because every process eventually "
     "reaches the front of the queue.\n\n"
     "**Disadvantages:** average waiting time can be very high, it suffers from the convoy effect, and because it "
     "is non-preemptive it is unsuitable for interactive or time-sharing systems."),
    ("FCFS", ["What is the convoy effect?", "Explain convoy effect in FCFS."],
     "The convoy effect happens in FCFS when one long CPU-bound process holds the CPU and many short processes "
     "queue up behind it, like cars stuck behind a slow truck.\n\n"
     "For example, if P1 needs 24 units and P2 and P3 need 3 units each and all arrive at 0, FCFS gives an "
     "average waiting time of 17. Running the short jobs first (SJF) brings it down to 3. The short I/O-bound "
     "processes also cannot issue their I/O, so device utilisation drops too."),
    ("FCFS", ["Is FCFS preemptive?", "Can FCFS cause starvation?"],
     "FCFS is non-preemptive: a running process keeps the CPU until it finishes or blocks. It does not cause "
     "starvation, because every process eventually reaches the front of the queue, although a short process may "
     "wait a long time behind a long one (the convoy effect)."),
    # ------------------------------------------------------------------ SJF
    ("SJF", ["What is SJF scheduling?", "Explain Shortest Job First.", "How does SJF work?"],
     "Shortest Job First gives the CPU to the ready process with the smallest next CPU burst. In its basic form it "
     "is non-preemptive: the chosen process runs to completion.\n\n"
     "Important rule: only processes that have already arrived can be chosen. A short job arriving later cannot "
     "jump ahead of the running process; for that you need the preemptive version, SRTF.\n\n"
     "Ties are broken by earlier arrival, then by lower process number."),
    ("SJF", ["Why is SJF called optimal?", "Prove that SJF gives minimum average waiting time."],
     "SJF gives the minimum average waiting time for a given set of processes that are all available.\n\n"
     "The reason: if a long job runs before a short one, swapping them reduces the short job's wait by the long "
     "job's length and increases the long job's wait by only the short job's length. Since the first reduction is "
     "bigger, every swap that puts a shorter job first lowers the total waiting time, so the order with the "
     "shortest jobs first is the best possible."),
    ("SJF", ["What is the main problem with SJF?", "Why is SJF hard to implement?"],
     "The scheduler does not know how long the next CPU burst will be. SJF can only be approximated by predicting "
     "the next burst from past behaviour, usually with exponential averaging. SJF can also starve long processes "
     "if short ones keep arriving."),
    ("SJF", ["How is the next CPU burst predicted?", "Explain exponential averaging in SJF.",
             "What is the formula for predicting the next CPU burst?"],
     "The next burst is predicted with exponential averaging:\n\n"
     "τ(n+1) = α · t(n) + (1 − α) · τ(n)\n\n"
     "where t(n) is the actual length of the most recent burst, τ(n) is the previous prediction, and 0 ≤ α ≤ 1.\n\n"
     "- α = 0: recent history is ignored (τ(n+1) = τ(n)).\n"
     "- α = 1: only the last burst counts (τ(n+1) = t(n)).\n"
     "- α = 1/2 is common: recent and past history count equally.\n\n"
     "Example: τ(n) = 10, t(n) = 6, α = 0.5 gives τ(n+1) = 0.5 × 6 + 0.5 × 10 = 8."),
    ("SJF", ["Does SJF cause starvation?"],
     "Yes. If short processes keep arriving, a long process may keep being passed over and wait indefinitely. "
     "Aging, which gradually raises the priority of a process the longer it waits, is the usual fix."),
    ("SJF", ["What is the difference between SJF and SRTF?", "SJF vs SRTF?",
             "Non-preemptive SJF vs preemptive SJF?"],
     "Both pick the process with the shortest burst, but:\n\n"
     "- **SJF (non-preemptive)** decides only when the CPU becomes free. The chosen process runs to completion, "
     "even if a shorter job arrives meanwhile.\n"
     "- **SRTF (preemptive SJF)** re-checks at every arrival. If the new process needs less time than the "
     "running process has left, the running one is preempted.\n\n"
     "SRTF gives an equal or lower average waiting time, but costs more context switches and can starve long "
     "jobs more."),
    # ------------------------------------------------------------------ SRTF
    ("SRTF", ["What is SRTF scheduling?", "Explain Shortest Remaining Time First.", "How does SRTF work?"],
     "SRTF (Shortest Remaining Time First, also called preemptive SJF or STCF) always runs the process with the "
     "least remaining time.\n\n"
     "Whenever a new process arrives, compare its burst with the remaining time of the running process. If the "
     "new one is shorter, it preempts the running process, which goes back to the ready queue with its remaining "
     "time. Ties go to the earlier arrival, then the lower process number."),
    ("SRTF", ["When does preemption happen in SRTF?"],
     "Preemption can only happen when a new process arrives (or when the running process finishes and a new "
     "choice is made). At that moment the scheduler compares the new process's burst with the running process's "
     "remaining time; if the new one is strictly shorter, it takes the CPU. With equal times the running "
     "process keeps it under our tie rule, since it arrived earlier."),
    ("SRTF", ["How is waiting time calculated in SRTF?", "Why is WT not start time minus arrival in SRTF?"],
     "Use WT = TAT − BT, where TAT = CT − AT and CT is the end of the process's last box in the Gantt chart.\n\n"
     "Start time minus arrival time gives only the response time. In SRTF a process can be preempted and wait "
     "several times, and WT = TAT − BT counts all of those waits automatically."),
    ("SRTF", ["What are the advantages and disadvantages of SRTF?"],
     "**Advantages:** lowest average waiting time of the common algorithms, and short jobs get the CPU almost "
     "immediately.\n\n"
     "**Disadvantages:** needs burst-length prediction, causes more context switches than SJF, and long "
     "processes can starve if short ones keep arriving."),
    # ------------------------------------------------------------------ Priority
    ("Priority", ["What is priority scheduling?", "Explain priority scheduling.", "How does priority scheduling work?"],
     "Each process has a priority and the CPU goes to the ready process with the highest priority. In our course "
     "a lower number means higher priority (priority 1 beats priority 3). Ties are broken by earlier arrival, then "
     "by lower process number.\n\n"
     "It can be non-preemptive (the running process finishes first) or preemptive (a newly arrived "
     "higher-priority process takes the CPU immediately). SJF is a special case where the priority is the "
     "predicted burst length."),
    ("Priority", ["What is the difference between preemptive and non-preemptive priority scheduling?"],
     "In non-preemptive priority scheduling, a higher-priority process that arrives waits until the running "
     "process finishes; only then does the scheduler pick the highest-priority ready process.\n\n"
     "In preemptive priority scheduling, as soon as a process with higher priority than the running one arrives, "
     "the running process is put back in the ready queue and the new one runs."),
    ("Priority", ["What is starvation?", "What is starvation in priority scheduling?", "What is indefinite blocking?"],
     "Starvation (indefinite blocking) is when a ready process waits forever because other processes keep getting "
     "the CPU ahead of it. In priority scheduling, a low-priority process may never run if higher-priority "
     "processes keep arriving.\n\n"
     "It can happen in Priority, SJF and SRTF scheduling, and with fixed-priority multilevel queues. FCFS and "
     "Round Robin do not cause starvation."),
    ("Priority", ["What is aging?", "How is starvation solved?", "How does aging prevent starvation?"],
     "Aging gradually increases the priority of a process the longer it waits. For example, the scheduler might "
     "raise a waiting process's priority by one level every 15 minutes, so even the lowest-priority process "
     "eventually becomes the highest-priority one and runs. This removes starvation without giving up priority "
     "scheduling."),
    ("Priority", ["What is the difference between static and dynamic priority?"],
     "A static priority is fixed when the process is created and never changes. A dynamic priority is adjusted by "
     "the OS while the process runs, for example raised by aging when it waits long or raised briefly after I/O "
     "to keep interactive programs responsive (Windows does this with priority boosts)."),
    ("Priority", ["What is priority inversion?", "Explain priority inversion and how to solve it."],
     "Priority inversion is when a high-priority process waits for a resource held by a low-priority process, and "
     "a medium-priority process keeps preempting the low one, so the high-priority process is effectively blocked "
     "by a lower-priority one.\n\n"
     "The usual fix is priority inheritance: while the low-priority process holds the resource, it temporarily "
     "inherits the high priority, finishes quickly and releases it. A well-known case was NASA's Mars Pathfinder "
     "lander in 1997, which kept resetting until priority inheritance was turned on."),
    ("Priority", ["How is SJF related to priority scheduling?"],
     "SJF is priority scheduling where the priority is the predicted length of the next CPU burst: the shorter the "
     "burst, the higher the priority. That is also why SJF shares priority scheduling's starvation problem."),
    # ------------------------------------------------------------------ Round Robin
    ("Round Robin", ["What is Round Robin scheduling?", "Explain Round Robin.", "How does RR scheduling work?"],
     "Round Robin is designed for time-sharing. The ready queue is a circular FIFO queue, and each process gets "
     "the CPU for at most one time quantum q.\n\n"
     "If the process finishes within its quantum, it leaves. If not, it is preempted and goes to the back of the "
     "queue. In our convention, a process that arrives at the same moment a quantum expires joins the queue "
     "before the preempted process.\n\n"
     "It is fair and gives good response time, but its average turnaround is usually higher than SJF's."),
    ("Round Robin", ["What is a time quantum?", "What is a time slice?"],
     "The time quantum (time slice) is the maximum time a process may run in one turn under Round Robin, "
     "typically 10 to 100 milliseconds in real systems. When it expires, a timer interrupt preempts the process "
     "and the next one in the queue runs."),
    ("Round Robin", ["How does the size of the time quantum affect Round Robin?", "What happens if the quantum is very large?",
                     "What happens if the quantum is very small?"],
     "- **Very large quantum**: every process finishes within one turn, so Round Robin behaves exactly like FCFS.\n"
     "- **Very small quantum**: response time is excellent, but the CPU spends a large share of its time on "
     "context switches instead of real work.\n\n"
     "The quantum should be large compared to the context-switch time. A common rule of thumb is that about 80% "
     "of CPU bursts should be shorter than the quantum."),
    ("Round Robin", ["What is the maximum waiting time in Round Robin?",
                     "How long does a process wait for its next turn in RR?"],
     "With n processes in the ready queue and quantum q, a process never waits more than (n − 1) × q time units "
     "before its next turn, because at most every other process runs one quantum ahead of it. For example, with "
     "5 processes and q = 20 ms, each process gets the CPU again within 80 ms."),
    ("Round Robin", ["Does a larger time quantum always improve turnaround time?"],
     "No. Average turnaround time does not change in a simple direction as the quantum grows. It improves when "
     "most processes can finish their burst within one quantum, but it can go up or down for other values. "
     "That is why the quantum is chosen mainly by the 80% rule and the context-switch cost."),
    ("Round Robin", ["Round Robin vs FCFS?", "Difference between Round Robin and FCFS?"],
     "FCFS is non-preemptive: each process runs to completion in arrival order. Round Robin is FCFS with "
     "preemption after each time quantum.\n\n"
     "Round Robin gives much better response time and avoids the convoy effect, but has more context-switch "
     "overhead and often a higher average turnaround. With a quantum larger than every burst, Round Robin is "
     "the same as FCFS."),
    ("Round Robin", ["Can Round Robin cause starvation?"],
     "No. Every process in the ready queue gets a turn within (n − 1) × q time units, so no process waits "
     "forever."),
    # ------------------------------------------------------------------ multilevel
    ("Multilevel queues", ["What is multilevel queue scheduling?", "Explain multilevel queue scheduling."],
     "The ready queue is split into several separate queues, for example system, interactive and batch "
     "processes. Each process is permanently assigned to one queue based on its type, and each queue has its own "
     "algorithm, for example Round Robin for interactive and FCFS for batch.\n\n"
     "Between queues, scheduling is either fixed-priority (a lower queue runs only when the higher ones are "
     "empty, which risks starvation) or time-sliced (for example 80% of CPU time to interactive and 20% to "
     "batch)."),
    ("Multilevel queues", ["What is a multilevel feedback queue?", "Explain MLFQ.", "How does MLFQ work?"],
     "A multilevel feedback queue (MLFQ) also has several priority queues, but processes can move between them "
     "based on their behaviour:\n\n"
     "1. If A's priority is higher than B's, A runs.\n2. Processes in the same queue run Round Robin.\n"
     "3. A new process starts in the highest queue.\n"
     "4. When a process uses up its time allotment at a level, it moves down one level.\n"
     "5. Periodically, all processes are moved back to the top queue (a priority boost).\n\n"
     "Short, interactive jobs finish while still at high priority, and long CPU-bound jobs sink to lower queues, "
     "so MLFQ approximates SJF without knowing burst lengths in advance."),
    ("Multilevel queues", ["Multilevel queue vs multilevel feedback queue?",
                           "What is the difference between MLQ and MLFQ?"],
     "In a multilevel queue, each process is permanently assigned to one queue. In a multilevel feedback queue, "
     "processes move between queues: a process that uses a lot of CPU time moves down, and processes that wait "
     "long are moved up (aging or a periodic priority boost), which prevents starvation."),
    ("Multilevel queues", ["What parameters define a multilevel feedback queue?"],
     "An MLFQ scheduler is defined by:\n\n- the number of queues,\n- the scheduling algorithm for each queue,\n"
     "- the rule for moving a process down to a lower-priority queue,\n- the rule for moving a process up,\n"
     "- which queue a new process enters.\n\n"
     "This makes it the most flexible scheduler, but also the hardest to tune."),
    ("Multilevel queues", ["How does MLFQ prevent starvation and gaming?", "Why does MLFQ need a priority boost?"],
     "Without changes, long-running jobs at the bottom could starve if many interactive jobs keep the top queues "
     "busy. MLFQ fixes this by periodically moving every process back to the top queue (a priority boost).\n\n"
     "To stop a program from gaming the scheduler by giving up the CPU just before its quantum ends, MLFQ counts "
     "the total CPU time used at each level: once a process has used its allotment, it moves down, however it "
     "split that time."),
    # ------------------------------------------------------------------ multiprocessor
    ("Multiprocessor", ["What is the difference between asymmetric and symmetric multiprocessing?",
                        "AMP vs SMP scheduling?"],
     "In asymmetric multiprocessing, one master processor makes all scheduling decisions and the others only run "
     "user code, which is simple but makes the master a bottleneck. In symmetric multiprocessing (SMP), every "
     "processor schedules itself, either from one shared ready queue or from its own private queue. All modern "
     "general-purpose OSs use SMP."),
    ("Multiprocessor", ["What is processor affinity?", "Soft vs hard affinity?"],
     "Processor affinity means keeping a process on the processor it last ran on, because that processor's cache "
     "already holds its data. Moving it means the new cache is cold and must be refilled.\n\n"
     "With soft affinity the OS tries to keep the process on the same CPU but may move it. With hard affinity "
     "the process is restricted to a chosen set of CPUs (on Linux, with sched_setaffinity)."),
    ("Multiprocessor", ["What is load balancing?", "Push vs pull migration?"],
     "Load balancing keeps work spread evenly across processors so none sits idle while others are overloaded.\n\n"
     "- **Push migration**: a periodic task checks the loads and pushes processes from busy CPUs to less busy ones.\n"
     "- **Pull migration**: an idle CPU pulls a waiting process from a busy CPU.\n\n"
     "Load balancing works against processor affinity, because moving a process loses its warm cache."),
    ("Multiprocessor", ["Why use per-CPU run queues in multiprocessor scheduling?"],
     "With one shared queue, every CPU must lock it to pick a process, which becomes a bottleneck as the number "
     "of CPUs grows, and processes bounce between CPUs and lose their cache. Per-CPU queues avoid the shared lock "
     "and keep processes on one CPU, giving natural affinity. The cost is that the queues can become unbalanced, "
     "so load balancing is needed."),
    ("Multiprocessor", ["What is multicore scheduling with hardware threads?"],
     "When a core waits on a memory access (a memory stall), it can switch to another hardware thread and keep "
     "working. Scheduling then happens at two levels: the OS decides which software thread runs on each hardware "
     "thread, and the core decides which of its hardware threads runs at each moment."),
    # ------------------------------------------------------------------ real-time
    ("Real-time", ["What is the difference between hard and soft real-time systems?"],
     "A hard real-time system must meet every deadline; missing one is a failure (for example an airbag "
     "controller). A soft real-time system gives critical tasks preference but does not guarantee every deadline "
     "(for example video streaming). Both need preemptive, priority-based scheduling with low latency."),
    ("Real-time", ["What is rate-monotonic scheduling?", "Explain rate monotonic scheduling."],
     "Rate-monotonic scheduling gives each periodic task a fixed priority based on its period: the shorter the "
     "period, the higher the priority. It is preemptive and is the best fixed-priority algorithm, meaning if any "
     "fixed-priority assignment can meet the deadlines, rate-monotonic can.\n\n"
     "Its CPU utilisation is bounded by N(2^(1/N) − 1) for N tasks: 100% for one task, about 83% for two, and "
     "about 69% as N grows large."),
    ("Real-time", ["What is earliest deadline first scheduling?", "Explain EDF."],
     "Earliest Deadline First gives the highest priority to the task whose deadline is nearest, so priorities "
     "change dynamically. It is preemptive and, in theory, can schedule any set of periodic tasks with total "
     "utilisation up to 100%, which is better than rate-monotonic. In practice, context switching and interrupt "
     "handling make 100% unreachable."),
    ("Real-time", ["Rate monotonic vs EDF?", "Compare RMS and EDF."],
     "Rate-monotonic uses static priorities based on period; EDF uses dynamic priorities based on the nearest "
     "deadline. EDF can reach up to 100% CPU utilisation, while rate-monotonic is only guaranteed up to "
     "N(2^(1/N) − 1), about 69% for many tasks. Rate-monotonic is simpler and more predictable under overload."),
    ("Real-time", ["What are periodic tasks in real-time scheduling?"],
     "A periodic task needs the CPU at regular intervals. It has a processing time t, a deadline d and a period "
     "p, with 0 ≤ t ≤ d ≤ p. Its rate is 1/p and its CPU utilisation is t/p. A set of tasks can only be "
     "scheduled if the total utilisation is at most 1 (100%)."),
    # ------------------------------------------------------------------ real OS
    ("Real OS", ["How does the Linux CFS scheduler work?", "What is the Completely Fair Scheduler?"],
     "CFS gives each task a fair share of the CPU. It tracks each task's virtual runtime (vruntime), the CPU time "
     "it has used, scaled by its nice value, and always runs the task with the smallest vruntime. Tasks are kept "
     "in a red-black tree ordered by vruntime, so finding the next task is fast. A task that has run less, such as "
     "an interactive one that often sleeps, naturally gets picked sooner."),
    ("Real OS", ["What are nice values in Linux?", "How does nice affect scheduling?"],
     "The nice value ranges from −20 (highest priority) to +19 (lowest), default 0. In CFS it sets a task's "
     "weight: each step of one nice level changes a task's CPU share by roughly 10% relative to others, and a "
     "lower nice value makes vruntime grow more slowly, so the task runs more often."),
    ("Real OS", ["What is EEVDF in Linux?"],
     "EEVDF (Earliest Eligible Virtual Deadline First) replaced CFS as Linux's default scheduler in kernel 6.6. "
     "Like CFS it aims for fairness, but it also gives each task a virtual deadline and runs the eligible task "
     "with the earliest one, which handles latency-sensitive tasks better."),
    ("Real OS", ["What are SCHED_FIFO, SCHED_RR and SCHED_OTHER in Linux?", "Linux scheduling policies?"],
     "- **SCHED_OTHER (SCHED_NORMAL)**: the default time-sharing policy for normal tasks, handled by the fair "
     "scheduler using nice values.\n"
     "- **SCHED_FIFO**: real-time, fixed priority 1 to 99, no time slice; a task runs until it blocks, yields or "
     "is preempted by a higher-priority task.\n"
     "- **SCHED_RR**: like SCHED_FIFO, but tasks of equal priority share the CPU in Round Robin with a time "
     "quantum.\n\n"
     "Real-time tasks always run before normal tasks."),
    ("Real OS", ["How does Windows schedule threads?", "Windows scheduling priorities?"],
     "Windows uses preemptive, priority-based scheduling with 32 priority levels, 0 to 31. Levels 16 to 31 are "
     "the real-time class and 1 to 15 are the variable class; level 0 is reserved for the zero-page thread. The "
     "highest-priority ready thread runs, and threads of equal priority share the CPU in Round Robin. Windows "
     "temporarily boosts the priority of threads that finish waiting, for example on I/O, to keep interactive "
     "programs responsive."),
    # ------------------------------------------------------------------ comparisons
    ("Comparison", ["Which scheduling algorithms can cause starvation?"],
     "SJF, SRTF and Priority scheduling can starve processes, and so can a multilevel queue with fixed priorities "
     "between queues. FCFS and Round Robin cannot, because every process eventually gets the CPU. Aging is the "
     "usual fix."),
    ("Comparison", ["Which scheduling algorithm gives the minimum average waiting time?"],
     "Among non-preemptive algorithms, SJF gives the minimum average waiting time for a set of available "
     "processes. Its preemptive version, SRTF, gives an equal or lower average waiting time when processes arrive "
     "at different times. Both need to know or predict burst lengths."),
    ("Comparison", ["Which scheduling algorithm is best for interactive systems?",
                    "Which algorithm gives the best response time?"],
     "Round Robin, or a multilevel feedback queue built on it, is best for interactive systems: every process "
     "gets the CPU within (n − 1) × q, so response time stays low and predictable. FCFS and non-preemptive SJF "
     "are poor choices, because one long job can make an interactive user wait."),
    ("Comparison", ["Compare FCFS, SJF, SRTF, Priority and Round Robin.", "Summarise the scheduling algorithms."],
     "| Algorithm | Preemptive | Strength | Weakness |\n|---|---|---|---|\n"
     "| FCFS | No | Simple, no starvation | Convoy effect, long waits |\n"
     "| SJF | No | Minimum average WT | Needs burst prediction, starvation |\n"
     "| SRTF | Yes | Lowest average WT | More context switches, starvation |\n"
     "| Priority | Either | Flexible | Starvation (fixed by aging) |\n"
     "| Round Robin | Yes | Fair, good response time | Overhead, higher turnaround |"),
    ("Comparison", ["Which scheduling algorithm should be used for batch systems?"],
     "Batch systems care about throughput and turnaround, not response time, so non-preemptive algorithms such as "
     "SJF (if burst lengths can be estimated) or FCFS work well: they keep context switches to a minimum and SJF "
     "minimises average waiting time."),
    # ------------------------------------------------------------------ proportional share
    ("Proportional share", ["What is lottery scheduling?", "Explain proportional share scheduling."],
     "Lottery scheduling gives each process a number of tickets that represent its share of the CPU. At each "
     "scheduling decision the scheduler draws a random ticket, and the process holding it runs. A process with "
     "75 of 100 tickets gets about 75% of the CPU over time. It is simple and fair on average, but not exact over "
     "short periods."),
    ("Proportional share", ["What is stride scheduling?"],
     "Stride scheduling is a deterministic version of lottery scheduling. Each process has a stride, equal to a "
     "large number divided by its tickets, and a pass value. The scheduler always runs the process with the "
     "lowest pass value and then adds its stride to that pass value, so processes with more tickets run "
     "proportionally more often, exactly rather than on average."),
]

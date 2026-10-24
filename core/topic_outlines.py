"""
What each Learn topic covers. Lessons are built from these outlines so they stay on the topic,
cover every syllabus point, and go deeper at higher levels.

  cover      : the sub-topics a lesson must explain, in teaching order
  facts      : precise facts / formulas the lesson must state correctly
  advanced   : extra depth for the Advanced level (proof ideas, edge cases, real OS)
  not_here   : neighbouring topics to mention in at most one line (they have their own lesson)
  example    : (algorithm, processes, quantum) solved by the engine for a worked example, or None
  query      : extra search words for retrieval
"""

OUTLINES = {
    "Scheduling Fundamentals": {
        "cover": [
            "why scheduling exists: multiprogramming and keeping the CPU busy while a process waits for I/O",
            "the CPU-I/O burst cycle; CPU-bound vs I/O-bound processes; why most CPU bursts are short",
            "process states (new, ready, running, waiting, terminated) and the transitions between them",
            "the ready queue and device queues; the PCB",
            "long-term, short-term and medium-term schedulers; degree of multiprogramming; swapping",
            "the dispatcher, context switch and dispatch latency",
            "the four moments a scheduling decision can happen",
            "preemptive vs non-preemptive (cooperative) scheduling, with the cost of each",
        ],
        "facts": [
            "Decisions happen when a process: (1) running -> waiting, (2) running -> ready, (3) waiting -> ready, "
            "(4) terminates. Only 1 and 4 -> non-preemptive; 2 and 3 also -> preemptive.",
            "Short-term scheduler runs every few milliseconds, so it must be fast; long-term runs rarely.",
            "A context switch saves the old process's state in its PCB and loads the new one's; it is pure overhead.",
        ],
        "advanced": [
            "why preemption creates race conditions on shared kernel data and what that means for the OS",
            "how the histogram of CPU-burst lengths (many short, few long) motivates the choice of algorithm",
            "thread scheduling: process-contention scope vs system-contention scope",
            "measuring dispatch latency and why it limits how small a time slice can be",
        ],
        "not_here": "scheduling criteria and individual algorithms (FCFS, SJF, RR...) have their own lessons",
        "example": None,
        "query": "CPU-I/O burst cycle process states schedulers dispatcher context switch preemptive",
    },
    "Scheduling Criteria": {
        "cover": [
            "CPU utilisation and throughput (maximise)",
            "turnaround time, waiting time and response time (minimise), with exact definitions",
            "the formulas TAT = CT - AT, WT = TAT - BT, RT = first start - AT, and averages",
            "reading CT, first start and idle time from a Gantt chart",
            "why the algorithm only changes waiting time, not burst time",
            "which criterion matters for batch vs interactive systems; variance of response time",
        ],
        "facts": [
            "TAT = CT - AT; WT = TAT - BT; RT = first time on CPU - AT.",
            "In non-preemptive algorithms RT = WT; in preemptive ones WT >= RT because a process can wait several times.",
            "Throughput = processes / total time; utilisation = busy time / total time.",
            "Common mistakes: TAT = CT and WT = CT - BT are only correct when AT = 0.",
        ],
        "advanced": [
            "why minimising average waiting time and minimising response time can conflict (SJF vs RR)",
            "optimising the average vs the maximum vs the variance, and fairness",
            "how idle time affects utilisation and throughput but not any process's waiting time",
        ],
        "not_here": "how each algorithm builds its Gantt chart is covered in the algorithm lessons",
        "example": ("SRTF", [("P1", 0, 7, 0), ("P2", 2, 4, 0), ("P3", 4, 1, 0), ("P4", 5, 4, 0)], None),
        "query": "scheduling criteria utilisation throughput turnaround waiting response time formulas",
    },
    "FCFS": {
        "cover": [
            "the rule: run processes in order of arrival using a FIFO queue; non-preemptive",
            "how to build the Gantt chart, including idle time when no process has arrived",
            "a full worked example with CT, TAT, WT and averages",
            "the convoy effect and why it lowers CPU and device utilisation",
            "why the average waiting time depends heavily on arrival order",
            "advantages and disadvantages; no starvation",
        ],
        "facts": [
            "FCFS never starves a process.",
            "Example: bursts 24, 3, 3 all at time 0 give average WT 17 in that order, but 3 if the short jobs go first.",
        ],
        "advanced": [
            "the convoy effect with I/O-bound and CPU-bound processes and its effect on device utilisation",
            "why FCFS is unsuitable for time-sharing systems",
            "FCFS as the base of Round Robin (RR with a quantum larger than every burst equals FCFS)",
        ],
        "not_here": "SJF and Round Robin have their own lessons; mention them only as a one-line contrast",
        "example": ("FCFS", [("P1", 0, 5, 0), ("P2", 1, 3, 0), ("P3", 2, 8, 0), ("P4", 3, 6, 0)], None),
        "query": "FCFS first come first served FIFO convoy effect",
    },
    "SJF": {
        "cover": [
            "the rule: when the CPU is free, pick the arrived process with the shortest next CPU burst; "
            "non-preemptive",
            "only processes that have already arrived can be chosen; tie-breaking",
            "a full worked example with arrivals",
            "why SJF is optimal for average waiting time (the exchange argument)",
            "predicting the next burst with exponential averaging, with a numeric example",
            "starvation of long jobs and the fix (aging)",
        ],
        "facts": [
            "tau(n+1) = alpha * t(n) + (1 - alpha) * tau(n), 0 <= alpha <= 1; alpha = 0 ignores recent history, "
            "alpha = 1 uses only the last burst.",
            "SJF minimises average waiting time for a given set of available processes.",
        ],
        "advanced": [
            "the exchange-argument proof of optimality, stated precisely",
            "why optimality fails when jobs arrive at different times, and how SRTF fixes it",
            "SJF as priority scheduling with priority = predicted burst; use in long-term scheduling",
        ],
        "not_here": "SRTF (the preemptive version) has its own lesson; contrast it in one line",
        "example": ("SJF", [("P1", 0, 7, 0), ("P2", 2, 4, 0), ("P3", 4, 1, 0), ("P4", 5, 4, 0)], None),
        "query": "shortest job first SJF optimal exponential averaging burst prediction",
    },
    "SRTF": {
        "cover": [
            "the rule: always run the arrived process with the shortest remaining time; preemptive",
            "when preemption happens (on arrival) and how ties are broken",
            "a full worked example showing each preemption",
            "why waiting time must be TAT - BT (a process waits several times), and response time vs waiting time",
            "advantages and disadvantages: lowest average WT, more context switches, starvation",
        ],
        "facts": [
            "SRTF is also called preemptive SJF or STCF (shortest time-to-completion first).",
            "SRTF's average waiting time is less than or equal to non-preemptive SJF's for the same processes.",
        ],
        "advanced": [
            "why SRTF is optimal for average waiting time when jobs arrive over time",
            "the cost of extra context switches and why real systems approximate it",
            "starvation scenarios and how MLFQ approximates SRTF without knowing burst lengths",
        ],
        "not_here": "non-preemptive SJF has its own lesson; contrast it in one line",
        "example": ("SRTF", [("P1", 0, 7, 0), ("P2", 2, 4, 0), ("P3", 4, 1, 0), ("P4", 5, 4, 0)], None),
        "query": "SRTF shortest remaining time first preemptive SJF STCF",
    },
    "Priority Scheduling": {
        "cover": [
            "the rule: run the highest-priority arrived process (lower number = higher priority in our course)",
            "non-preemptive vs preemptive priority, with a worked example of each on the same processes",
            "static vs dynamic priorities",
            "starvation (indefinite blocking) and aging",
            "priority inversion and priority inheritance",
        ],
        "facts": [
            "Ties go to the earlier arrival, then the lower process number.",
            "SJF is priority scheduling where priority = predicted burst length.",
            "Priority inversion: a medium-priority process preempts a low-priority process that holds a resource "
            "the high-priority process needs; priority inheritance fixes it (Mars Pathfinder, 1997).",
        ],
        "advanced": [
            "designing an aging rule and what it guarantees",
            "real systems: Windows 32 priority levels with priority boosts; Linux real-time priorities 1-99 and nice "
            "values",
            "priority inversion in detail with a timeline",
        ],
        "not_here": "multilevel queues build on priorities but have their own lesson",
        "example": ("PRIORITY_P", [("P1", 0, 4, 3), ("P2", 1, 3, 1), ("P3", 2, 2, 4), ("P4", 3, 5, 2)], None),
        "query": "priority scheduling preemptive non-preemptive starvation aging priority inversion",
    },
    "Round Robin": {
        "cover": [
            "the rule: circular FIFO queue, each process runs at most one time quantum q",
            "the ready-queue order when a new arrival and a preempted process come back at the same time",
            "a full worked example showing the queue after every quantum",
            "the effect of the quantum size: large q -> FCFS, small q -> many context switches",
            "the (n - 1) x q bound on waiting for the next turn; the 80% rule of thumb",
            "RR vs FCFS and SJF: better response time, usually higher turnaround",
        ],
        "facts": [
            "Our convention: a process arriving when a quantum expires joins the queue before the preempted process.",
            "No process waits more than (n - 1) x q for its next turn; RR never starves a process.",
            "Average turnaround time does not necessarily improve as q grows.",
        ],
        "advanced": [
            "choosing q relative to context-switch time, with a numeric overhead calculation",
            "Linux SCHED_RR and sched_rr_get_interval; Windows round robin within a priority level",
            "RR as the building block of multilevel feedback queues",
        ],
        "not_here": "multilevel feedback queues have their own lesson",
        "example": ("RR", [("P1", 0, 5, 0), ("P2", 1, 4, 0), ("P3", 2, 2, 0), ("P4", 4, 1, 0)], 2),
        "query": "round robin time quantum time slice context switch ready queue",
    },
    "Multilevel Queue & Feedback Queue": {
        "cover": [
            "multilevel queue: separate queues, permanent assignment, a different algorithm per queue",
            "scheduling between queues: fixed priority vs time slicing (e.g. 80/20)",
            "multilevel feedback queue: processes move between queues based on behaviour",
            "the MLFQ rules (higher queue first, RR within a queue, new jobs start at the top, demotion after using "
            "the allotment, periodic priority boost)",
            "the parameters that define an MLFQ",
            "how MLFQ favours interactive jobs and approximates SJF/SRTF without knowing burst lengths",
        ],
        "facts": [
            "Example MLFQ: queue 0 RR q=8, queue 1 RR q=16, queue 2 FCFS.",
            "The priority boost prevents starvation; counting total CPU time per level prevents gaming.",
        ],
        "advanced": [
            "a step-by-step trace of one long job and one interactive job through an MLFQ",
            "gaming the scheduler and how allotment accounting stops it",
            "tuning problems (number of queues, quanta, boost period)",
        ],
        "not_here": "plain Round Robin and Priority have their own lessons",
        "example": None,
        "query": "multilevel queue multilevel feedback queue MLFQ rules priority boost allotment",
    },
    "Multiprocessor & Real-Time Scheduling": {
        "cover": [
            "asymmetric vs symmetric multiprocessing; shared vs per-CPU ready queues",
            "processor affinity (soft and hard) and why caches make it matter",
            "load balancing: push and pull migration, and its conflict with affinity",
            "hard vs soft real-time systems; periodic tasks with t, d, p",
            "rate-monotonic scheduling and its utilisation bound",
            "earliest deadline first and how it compares with rate-monotonic",
        ],
        "facts": [
            "Rate-monotonic bound: U <= N(2^(1/N) - 1): 1.0 for N=1, about 0.83 for N=2, about 0.69 as N grows.",
            "EDF can schedule any task set with total utilisation up to 1 (in theory).",
            "Utilisation of a periodic task = t / p.",
        ],
        "advanced": [
            "a rate-monotonic schedulability check with numbers, and an EDF schedule for a set RM cannot guarantee",
            "Linux: per-CPU run queues, scheduling domains for load balancing, sched_setaffinity, SCHED_FIFO/SCHED_RR",
            "multicore and hardware threads (memory stalls)",
        ],
        "not_here": "single-CPU algorithms have their own lessons",
        "example": None,
        "query": "multiprocessor scheduling processor affinity load balancing real-time rate monotonic EDF",
    },
}


# ======================================================================= the rest of the syllabus
# For non-scheduling numerical topics, "example" is {"algo": ..., "inputs": {...}} for core/os_solvers.py.
OUTLINES.update({
    "OS Introduction & Structure": {
        "cover": [
            "what an operating system is: resource allocator and control program; user view vs system view",
            "goals: convenience, efficiency, and the ability to evolve",
            "computer system components: hardware, OS, application programs, users",
            "kernel vs shell; dual-mode operation (user mode and kernel mode) and the mode bit",
            "OS structures: monolithic, layered, microkernel, modular (loadable modules) and hybrid, with examples",
            "key abstractions: process, virtual memory, file, device, thread",
        ],
        "facts": [
            "The kernel is the one program running at all times; the shell is a user program that reads commands.",
            "Privileged instructions can only run in kernel mode; a system call switches the CPU to kernel mode.",
            "Linux is monolithic with loadable modules; macOS/iOS (XNU) and Windows are hybrids; Mach and QNX are microkernels.",
        ],
        "advanced": [
            "performance vs reliability trade-off between monolithic kernels and microkernels (message passing cost)",
            "why modular kernels are the common compromise",
            "bootstrapping: firmware, bootloader, kernel initialisation",
        ],
        "not_here": "system calls and interrupts have their own lesson",
        "example": None,
        "query": "operating system definition goals kernel shell dual mode monolithic layered microkernel modular hybrid",
    },
    "System Calls & Interrupts": {
        "cover": [
            "what a system call is and why user programs need it (controlled entry into the kernel)",
            "the system call life cycle: library wrapper, trap, system-call number and table, handler, return",
            "types of system calls: process control, file management, device management, information, communication, protection",
            "parameter passing: registers, a block in memory, the stack",
            "system call vs ordinary function call",
            "interrupts: hardware vs software (traps), the interrupt vector, saving state and returning",
        ],
        "facts": [
            "Examples: fork, exec, exit, wait (process); open, read, write, close (files); pipe, shmget (communication).",
            "A trap (software interrupt) is raised by an error or a system call; a hardware interrupt comes from a device.",
            "The interrupt vector holds the addresses of the interrupt service routines.",
        ],
        "advanced": [
            "the cost of a mode switch and why batching (e.g. buffered I/O) reduces system calls",
            "interrupt priority and masking; polling vs interrupts vs DMA",
        ],
        "not_here": "process creation with fork/exec is covered under Processes",
        "example": None,
        "query": "system call trap interrupt vector types of system calls parameter passing kernel mode",
    },
    "Processes & Process Operations": {
        "cover": [
            "process vs program; the memory layout of a process: text, data, heap, stack",
            "process states (new, ready, running, waiting, terminated) and transitions",
            "the process control block (PCB) and what it stores",
            "context switch: saving and loading state, and why it is overhead",
            "process creation: fork(), exec(), wait(); the process tree; exit()",
            "zombie and orphan processes; cooperating vs independent processes",
        ],
        "facts": [
            "fork() returns 0 in the child and the child's PID in the parent; -1 on failure.",
            "After n calls to fork() in sequence, there are 2^n processes in total (2^n - 1 new ones).",
            "A zombie has terminated but its parent has not called wait(); an orphan's parent has terminated (adopted by init/systemd).",
        ],
        "advanced": [
            "copy-on-write after fork() and why exec() right after fork() is cheap",
            "counting printf outputs in fork() puzzles",
            "Chrome's multi-process architecture and Android's process importance hierarchy",
        ],
        "not_here": "CPU scheduling of processes has its own unit",
        "example": None,
        "query": "process concept states PCB context switch fork exec wait zombie orphan process creation termination",
    },
    "Threads & Multithreading": {
        "cover": [
            "thread vs process: what threads share (code, data, files) and what each has (registers, stack, PC)",
            "benefits: responsiveness, resource sharing, economy, scalability",
            "user-level vs kernel-level threads",
            "multithreading models: many-to-one, one-to-one, many-to-many",
            "thread libraries (Pthreads, Java, Windows) and implicit threading (thread pools)",
            "concurrency vs parallelism",
        ],
        "facts": [
            "Linux and Windows use the one-to-one model.",
            "In many-to-one, one blocking system call blocks the whole process and threads cannot run in parallel.",
            "Amdahl's law: speedup <= 1 / (S + (1 - S) / N) for serial fraction S on N cores.",
        ],
        "advanced": ["an Amdahl's law calculation", "thread cancellation and signal handling issues",
                     "hardware threads (hyper-threading)"],
        "not_here": "synchronization between threads has its own unit",
        "example": None,
        "query": "threads multithreading models user kernel threads pthreads amdahl concurrency parallelism",
    },
    "Inter-process Communication": {
        "cover": [
            "why processes cooperate; the two IPC models: shared memory and message passing",
            "the producer-consumer problem with a bounded buffer in shared memory",
            "message passing: send/receive, direct vs indirect (mailboxes), blocking vs non-blocking, buffering",
            "pipes (ordinary and named) as an example on Linux",
        ],
        "facts": [
            "In the circular bounded buffer with in/out pointers, the buffer can hold at most BUFFER_SIZE - 1 items.",
            "Shared memory is faster after setup; message passing is easier and works across machines.",
        ],
        "advanced": ["race conditions in the shared-memory producer-consumer code (motivates synchronization)",
                     "zero, bounded and unbounded capacity links"],
        "not_here": "semaphore solutions to producer-consumer are in Process Synchronization",
        "example": None,
        "query": "inter-process communication shared memory message passing producer consumer bounded buffer pipes mailbox",
    },
    "Critical Section & Peterson's Solution": {
        "cover": [
            "race conditions with a concrete counter++ / counter-- interleaving",
            "the critical-section problem: entry, critical, exit and remainder sections",
            "the three requirements: mutual exclusion, progress, bounded waiting",
            "Peterson's solution for two processes (flag[] and turn) and why it satisfies all three",
            "hardware support: test_and_set and compare_and_swap",
        ],
        "facts": [
            "Peterson: flag[i] = true; turn = j; while (flag[j] && turn == j); ... flag[i] = false;",
            "Peterson's solution may fail on modern CPUs that reorder memory operations unless memory barriers are used.",
        ],
        "advanced": ["proving mutual exclusion for Peterson's algorithm", "why disabling interrupts fails on multiprocessors"],
        "not_here": "semaphores and mutex locks have their own lesson",
        "example": None,
        "query": "race condition critical section mutual exclusion progress bounded waiting peterson test and set",
    },
    "Mutex Locks & Semaphores": {
        "cover": [
            "mutex locks: acquire() and release(), busy waiting and spinlocks",
            "semaphores: wait (P) and signal (V), counting vs binary",
            "using semaphores for mutual exclusion and for ordering (S1 before S2)",
            "semaphore implementation with a waiting queue instead of busy waiting",
            "deadlock and starvation with semaphores; priority inversion",
            "monitors and condition variables",
        ],
        "facts": [
            "wait(S): while (S <= 0); S--;   signal(S): S++;  (both must be atomic).",
            "With a waiting queue, a negative semaphore value's magnitude is the number of waiting processes.",
        ],
        "advanced": ["tracing semaphore values through a sequence of wait/signal operations",
                     "spinlocks are preferred on multiprocessors for short critical sections"],
        "not_here": "classical problems (bounded buffer, readers-writers, dining philosophers) have their own lesson",
        "example": None,
        "query": "mutex lock semaphore wait signal binary counting spinlock monitor condition variable",
    },
    "Classical Synchronization Problems": {
        "cover": [
            "bounded-buffer problem with semaphores mutex, empty and full",
            "readers-writers problem (first variation) with rw_mutex, mutex and read_count",
            "dining-philosophers problem, why the naive solution deadlocks, and remedies",
        ],
        "facts": [
            "Bounded buffer initial values: mutex = 1, empty = n, full = 0.",
            "In the first readers-writers solution writers may starve.",
            "Remedies for dining philosophers: at most 4 at the table, pick up both chopsticks together, or asymmetric order.",
        ],
        "advanced": ["what goes wrong if wait(mutex) and wait(empty) are swapped in the producer",
                     "a monitor solution to dining philosophers"],
        "not_here": "the semaphore definition itself is in Mutex Locks & Semaphores",
        "example": None,
        "query": "bounded buffer readers writers dining philosophers semaphore solution classical synchronization",
    },
    "Deadlock Characterization": {
        "cover": [
            "the system model: request, use, release",
            "the four necessary conditions: mutual exclusion, hold and wait, no preemption, circular wait",
            "resource-allocation graphs: request and assignment edges, single and multiple instances",
            "cycle vs deadlock: with single instances a cycle means deadlock; with multiple instances it may not",
            "wait-for graphs",
            "methods for handling deadlocks: prevention, avoidance, detection and recovery, ignoring (ostrich)",
        ],
        "facts": [
            "All four conditions must hold at the same time for a deadlock.",
            "A cycle in a resource-allocation graph is necessary but not sufficient when resources have several instances.",
        ],
        "advanced": ["drawing and reading a RAG with multiple instances that has a cycle but no deadlock",
                     "why most operating systems ignore deadlocks"],
        "not_here": "Banker's algorithm and detection are their own lessons",
        "example": None,
        "query": "deadlock necessary conditions mutual exclusion hold and wait no preemption circular wait resource allocation graph",
    },
    "Deadlock Prevention & Avoidance (Banker's)": {
        "cover": [
            "prevention: break one of the four conditions, with the cost of each",
            "avoidance: safe and unsafe states; a safe state means no deadlock, an unsafe state means one may occur",
            "Banker's algorithm data structures: Available, Max, Allocation, Need = Max - Allocation",
            "the safety algorithm step by step",
            "the resource-request algorithm: Request <= Need, Request <= Available, pretend, check safety",
        ],
        "facts": [
            "Need[i][j] = Max[i][j] - Allocation[i][j].",
            "Our convention: repeated passes over P0..Pn-1; any order satisfying the safety check is a valid safe sequence.",
            "Unsafe does not mean deadlocked; it means the OS can no longer guarantee to avoid deadlock.",
        ],
        "advanced": ["why circular wait is prevented with a total order on resource types",
                     "the cost of Banker's algorithm: O(m x n^2) per check"],
        "not_here": "detection after a deadlock happens has its own lesson",
        "example": {"algo": "BANKERS", "inputs": {"processes": ["P0", "P1", "P2", "P3", "P4"], "resources": ["A", "B", "C"],
                    "allocation": [[0, 1, 0], [2, 0, 0], [3, 0, 2], [2, 1, 1], [0, 0, 2]],
                    "max": [[7, 5, 3], [3, 2, 2], [9, 0, 2], [2, 2, 2], [4, 3, 3]], "available": [3, 3, 2]}},
        "query": "banker's algorithm safe state need matrix safety algorithm resource request deadlock avoidance prevention",
    },
    "Deadlock Detection & Recovery": {
        "cover": [
            "detection with single instances: cycles in the wait-for graph",
            "the detection algorithm for multiple instances (Available, Allocation, Request)",
            "how often to run detection",
            "recovery: terminate processes (all or one at a time) or preempt resources (victim, rollback, starvation)",
        ],
        "facts": [
            "Detection initialises Finish[i] = true for a process holding no resources.",
            "Processes with Finish[i] = false at the end are deadlocked.",
        ],
        "advanced": ["choosing a victim: priority, work done, resources held", "avoiding starvation of the same victim"],
        "not_here": "Banker's avoidance is in its own lesson",
        "example": {"algo": "DETECT", "inputs": {"processes": ["P0", "P1", "P2", "P3", "P4"], "resources": ["A", "B", "C"],
                    "allocation": [[0, 1, 0], [2, 0, 0], [3, 0, 3], [2, 1, 1], [0, 0, 2]],
                    "request_matrix": [[0, 0, 0], [2, 0, 2], [0, 0, 1], [1, 0, 0], [0, 0, 2]], "available": [0, 0, 0]}},
        "query": "deadlock detection algorithm wait-for graph recovery process termination resource preemption rollback",
    },
    "Memory Management Basics": {
        "cover": [
            "address binding at compile, load and execution time",
            "logical vs physical addresses; the MMU",
            "relocation (base) and limit registers for protection",
            "dynamic loading and dynamic linking (shared libraries)",
            "swapping",
        ],
        "facts": [
            "Physical address = relocation register + logical address, after checking logical address < limit.",
            "With execution-time binding, logical and physical addresses differ.",
        ],
        "advanced": ["a relocation/limit translation with a protection fault", "swapping costs and why mobile systems avoid it"],
        "not_here": "contiguous allocation and paging have their own lessons",
        "example": None,
        "query": "address binding logical physical address MMU relocation register limit register dynamic loading linking swapping",
    },
    "Contiguous Memory Allocation": {
        "cover": [
            "fixed vs variable partitions; holes",
            "the dynamic storage-allocation problem: first fit, best fit, worst fit, next fit",
            "a full worked example placing several processes",
            "internal vs external fragmentation; the 50-percent rule; compaction",
        ],
        "facts": [
            "Our convention: the chosen hole is split and the remainder stays free; next fit resumes at the hole used last.",
            "Fixed partitions cause internal fragmentation; variable partitions cause external fragmentation.",
            "50-percent rule: with first fit, about N/2 blocks are lost to fragmentation for N allocated blocks.",
        ],
        "advanced": ["why first fit is usually as good as best fit and faster", "compaction needs dynamic relocation"],
        "not_here": "paging (which removes external fragmentation) has its own lesson",
        "example": {"algo": "FIRST", "inputs": {"blocks": [100, 500, 200, 300, 600], "sizes": [212, 417, 112, 426],
                                                "names": ["P1", "P2", "P3", "P4"]}},
        "query": "contiguous memory allocation first fit best fit worst fit next fit fragmentation compaction partitions",
    },
    "Paging & Segmentation": {
        "cover": [
            "paging: pages, frames, page table; splitting a logical address into page number and offset",
            "translating a logical address to a physical address with a worked example",
            "the TLB, hit ratio and effective access time (EAT)",
            "protection bits, valid-invalid bit, shared pages",
            "multilevel, hashed and inverted page tables",
            "segmentation and the segment table (base, limit)",
        ],
        "facts": [
            "Logical address with page size 2^n: page number = address div 2^n, offset = address mod 2^n.",
            "EAT = h x (TLB time + memory time) + (1 - h) x (TLB time + 2 x memory time) (TLB time often ignored).",
            "Paging has no external fragmentation but can have internal fragmentation in the last page.",
        ],
        "advanced": ["page table size calculations for 32-bit and 64-bit addresses", "two-level paging address split"],
        "not_here": "page faults and replacement are under Virtual Memory",
        "example": None,
        "query": "paging page table frame offset TLB effective access time segmentation multilevel page table",
    },
    "Demand Paging": {
        "cover": [
            "virtual memory and why it helps; demand paging and lazy loading",
            "the page-fault handling steps",
            "effective access time with page faults",
            "copy-on-write",
        ],
        "facts": [
            "EAT = (1 - p) x memory access time + p x page-fault service time.",
            "Even a fault rate of 1 in 1,000 slows memory access down a lot because fault service takes milliseconds.",
        ],
        "advanced": ["solving for the maximum page-fault rate that keeps slowdown under 10%", "pure demand paging"],
        "not_here": "replacement algorithms have their own lesson",
        "example": None,
        "query": "virtual memory demand paging page fault handling effective access time copy on write",
    },
    "Page Replacement": {
        "cover": [
            "when replacement is needed and the basic steps (victim, dirty bit)",
            "FIFO, Optimal (OPT) and LRU, each with the frame table for a reference string",
            "counting page faults, hits and hit ratio",
            "Belady's anomaly (FIFO) and stack algorithms (LRU, OPT never show it)",
            "LRU approximations: reference bit, second chance (clock)",
        ],
        "facts": [
            "OPT replaces the page used farthest in the future and gives the fewest possible faults; it needs future knowledge.",
            "Classic string 7 0 1 2 0 3 0 4 2 3 0 3 2 1 2 0 1 7 0 1 with 3 frames: FIFO 15, LRU 12, OPT 9 faults.",
            "1 2 3 4 1 2 5 1 2 3 4 5 with FIFO: 9 faults with 3 frames but 10 with 4 frames (Belady's anomaly).",
        ],
        "advanced": ["why LRU is a stack algorithm", "implementing LRU with counters or a stack", "the clock algorithm"],
        "not_here": "thrashing and the working set have their own lesson",
        "example": {"algo": "LRU", "inputs": {"refs": [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2], "frames": 3}},
        "query": "page replacement FIFO LRU optimal page fault reference string frames belady anomaly",
    },
    "Thrashing & Working Set": {
        "cover": [
            "what thrashing is and why CPU utilisation collapses as multiprogramming rises",
            "the locality model",
            "the working-set model: window delta, working-set size, total demand D",
            "page-fault frequency (PFF) control",
            "frame allocation: equal vs proportional, global vs local replacement",
        ],
        "facts": [
            "If D = sum of working-set sizes > available frames, thrashing will occur, so a process should be suspended.",
            "Proportional allocation: a_i = (s_i / S) x m frames.",
        ],
        "advanced": ["computing a working set for a given window on a reference string", "a proportional allocation calculation"],
        "not_here": "page replacement algorithms have their own lesson",
        "example": None,
        "query": "thrashing working set locality page fault frequency frame allocation proportional global local replacement",
    },
    "File Systems": {
        "cover": [
            "the file concept: attributes, operations, types",
            "access methods: sequential, direct, indexed",
            "directory structures: single-level, two-level, tree, acyclic graph (links)",
            "allocation methods: contiguous, linked (FAT), indexed (inode), with pros and cons",
            "free-space management: bit vector, linked list, grouping, counting",
            "inodes, hard links vs soft links",
        ],
        "facts": [
            "Contiguous allocation supports direct access but suffers external fragmentation.",
            "Linked allocation has no external fragmentation but poor direct access; FAT keeps the links in a table.",
            "A hard link shares the inode; a soft (symbolic) link is a separate file holding a path.",
        ],
        "advanced": ["maximum file size with direct, single, double and triple indirect blocks",
                     "bit-vector size calculation"],
        "not_here": "disk scheduling has its own lesson",
        "example": None,
        "query": "file system access methods directory structure allocation contiguous linked indexed inode free space",
    },
    "Disk Scheduling": {
        "cover": [
            "disk structure: platters, tracks, cylinders, sectors; seek time, rotational latency, transfer time",
            "FCFS, SSTF, SCAN, C-SCAN, LOOK and C-LOOK, each on the same request queue",
            "total head movement and average seek distance",
            "starvation in SSTF; why SCAN/C-SCAN give more uniform wait times",
        ],
        "facts": [
            "Classic queue 98 183 37 122 14 124 65 67, head 53, 0-199: FCFS 640, SSTF 236 cylinders.",
            "Our convention: SCAN and C-SCAN go to the disk edge; the C-SCAN / C-LOOK return jump is counted.",
        ],
        "advanced": ["SSTF is not optimal: a case where it loses", "choosing an algorithm for heavy vs light load"],
        "not_here": "file allocation methods are in File Systems",
        "example": {"algo": "SSTF", "inputs": {"requests": [98, 183, 37, 122, 14, 124, 65, 67], "head": 53,
                                               "max_cyl": 199, "direction": "up"}},
        "query": "disk scheduling FCFS SSTF SCAN C-SCAN LOOK C-LOOK seek time head movement cylinders",
    },
    "Linux Commands": {
        "cover": [
            "files and directories: pwd, ls (-l, -a), cd, mkdir, rmdir, touch, cp, mv, rm",
            "viewing text: cat, head, tail, less, wc, sort, uniq, cut, grep, tee",
            "permissions: rwx for user/group/others, chmod (symbolic and octal), chown",
            "processes: ps, top, kill, jobs, bg, fg, nice",
            "archives and system: tar, gzip/gunzip, df, du, mount, who, uname, cal, ssh, man",
            "pipes and redirection: |, >, >>, <, 2>",
        ],
        "facts": [
            "chmod 754 file gives rwx to the owner, r-x to the group and r-- to others.",
            "kill -9 PID sends SIGKILL, which cannot be caught; plain kill sends SIGTERM.",
        ],
        "advanced": ["combining commands with pipes, e.g. counting the most common words in a file",
                     "how ps and top get process information from /proc"],
        "not_here": "system calls behind these commands are in System Calls & Interrupts",
        "example": None,
        "query": "linux commands ls cat grep chmod ps kill pipe redirection tar man shell",
    },
})

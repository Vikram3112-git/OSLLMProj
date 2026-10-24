"""
Concept questions and answers for the units beyond CPU scheduling (fine-tuning data).

Same format as concept_qa.py: (topic, [question phrasings], answer). Topic names match config.UNITS.
Written from our course notes (knowledge_base/07-14), OSTEP and Silberschatz. Numbers in the answers
were checked with core/os_solvers.py or by hand.
"""

QA_MORE = [
    # ------------------------------------------------------------------ unit 1
    ("OS Introduction & Structure", ["What is an operating system?", "Define an operating system and its goals."],
     "An operating system is the program that manages the computer's hardware and provides services to "
     "application programs.\n\nIt is usually described in two ways: as a **resource allocator**, deciding how the "
     "CPU, memory, storage and devices are shared, and as a **control program**, supervising programs so errors and "
     "misuse don't harm the system. Its goals are convenience for the user, efficient use of the hardware, and the "
     "ability to evolve as new hardware and services are added."),
    ("OS Introduction & Structure", ["Monolithic vs microkernel?", "Compare monolithic, layered and microkernel structures."],
     "- **Monolithic**: the whole kernel is one program in one address space (traditional UNIX, Linux). Fast, "
     "because parts call each other directly, but a bug anywhere can crash the system.\n"
     "- **Layered**: each layer uses only the layers below it. Easy to debug, but layers are hard to define and "
     "requests pass through many of them.\n"
     "- **Microkernel**: only IPC, basic scheduling and low-level memory management stay in the kernel; drivers and "
     "file systems run as user-space servers (Mach, QNX). More reliable, but message passing adds overhead.\n\n"
     "Linux is monolithic with loadable kernel modules; Windows and macOS are hybrids."),
    ("OS Introduction & Structure", ["What is dual-mode operation?", "Why are there user mode and kernel mode?"],
     "The CPU has a mode bit: kernel mode (0) and user mode (1). Privileged instructions such as I/O, setting the "
     "timer and changing memory protection can only run in kernel mode.\n\nUser programs run in user mode. When they "
     "need a privileged service they make a system call, which traps into kernel mode, runs the kernel code and "
     "returns to user mode. This protects the OS and other programs from a faulty or malicious program; a timer "
     "interrupt makes sure the OS always gets control back."),
    ("System Calls & Interrupts", ["What is a system call?", "Explain what happens when a program calls read()."],
     "A system call is the controlled way for a user program to ask the kernel for a service.\n\n"
     "1. The program calls the C library wrapper `read()`.\n2. The wrapper puts the system-call number and "
     "parameters in registers and executes a trap instruction.\n3. The trap switches to kernel mode and jumps to the "
     "system-call handler.\n4. The handler looks up the number in the system-call table and runs the kernel function.\n"
     "5. The result goes in a register and the CPU returns to user mode.\n\n"
     "Types: process control (fork, exec, exit, wait), file management (open, read, write, close), device "
     "management (ioctl), information (getpid, time), communication (pipe, shmget, socket) and protection (chmod)."),
    ("System Calls & Interrupts", ["What is an interrupt?", "Difference between a trap and an interrupt?"],
     "An interrupt makes the CPU stop what it is doing and run an interrupt service routine.\n\n"
     "- A **hardware interrupt** comes from a device: a disk finishing a transfer, a key press, the timer.\n"
     "- A **trap** (software interrupt or exception) comes from the running program: an error such as division by "
     "zero, or a deliberate system call.\n\nThe CPU saves the program counter and state, looks up the handler in the "
     "interrupt vector, runs it, then restores the state. DMA lets a controller move a whole block and interrupt "
     "only once at the end, which is why it is used for fast devices."),
    # ------------------------------------------------------------------ unit 2
    ("Processes & Process Operations", ["What is a PCB?", "What does the process control block contain?"],
     "The process control block is the kernel's record of one process. It holds the process state, process ID, "
     "program counter, CPU registers, scheduling information (priority, queue pointers), memory-management "
     "information (base and limit registers or page tables), accounting information and I/O status (open files).\n\n"
     "On a context switch the kernel saves the running process's state into its PCB and loads the next process's "
     "state from its PCB. That switch is pure overhead."),
    ("Processes & Process Operations", ["How many processes are created by fork() three times?", "Explain fork()."],
     "fork() creates a child that is a copy of the parent. It returns 0 in the child, the child's PID in the parent, "
     "and -1 on failure.\n\nEvery existing process runs each later fork(), so the count doubles each time: after n "
     "calls there are 2^n processes, that is 2^n − 1 new ones. Three fork() calls give 2³ = 8 processes, 7 of them "
     "children.\n\nA child that has exited but has not been waited for is a **zombie**; a child whose parent exited "
     "first is an **orphan** and is adopted by init/systemd."),
    ("Threads & Multithreading", ["What is a thread?", "Process vs thread?"],
     "A thread is a unit of CPU execution inside a process. Threads of one process share its code, data and open "
     "files, but each has its own thread ID, program counter, registers and stack.\n\nCompared with processes, threads "
     "are cheaper to create and switch, share data easily, keep an application responsive while one thread blocks, "
     "and can run in parallel on multicore CPUs. The cost is that shared data needs synchronization."),
    ("Threads & Multithreading", ["Explain multithreading models.", "Many-to-one vs one-to-one vs many-to-many?"],
     "- **Many-to-one**: many user threads on one kernel thread. Cheap, but one blocking call blocks them all and "
     "they cannot use several cores.\n- **One-to-one**: each user thread has its own kernel thread (Linux, Windows). "
     "True parallelism, but each thread costs a kernel thread.\n- **Many-to-many**: many user threads multiplexed on "
     "a smaller or equal number of kernel threads, combining both advantages.\n\n"
     "Amdahl's law limits the gain: with a serial fraction of 0.25, two cores give at most 1 / (0.25 + 0.75/2) = 1.6 "
     "times speedup."),
    ("Inter-process Communication", ["Shared memory vs message passing?", "Explain the two IPC models."],
     "- **Shared memory**: processes share a region and read and write it directly. Fast after setup because no "
     "system call is needed per access, but the processes must synchronize themselves.\n"
     "- **Message passing**: processes send and receive messages through the kernel. Easier and works across "
     "machines, but every message costs a system call.\n\nPipes are a simple message-passing channel on UNIX: an "
     "ordinary pipe is one-way between parent and child; a named pipe (FIFO) can join unrelated processes."),
    ("Inter-process Communication", ["Explain the bounded buffer with in and out pointers."],
     "The producer and consumer share a circular buffer of size N with two indices: `in` (next free slot) and `out` "
     "(first full slot).\n\n- Empty when `in == out`.\n- Full when `(in + 1) % N == out`.\n- Producer: wait while "
     "full, `buffer[in] = item`, `in = (in + 1) % N`.\n- Consumer: wait while empty, `item = buffer[out]`, "
     "`out = (out + 1) % N`.\n\nWith this scheme the buffer holds at most N − 1 items. Using a shared counter instead "
     "causes a race on `counter++` and `counter--`, which is why synchronization is needed."),
    # ------------------------------------------------------------------ unit 4
    ("Critical Section & Peterson's Solution", ["What is the critical section problem?", "Requirements of a critical section solution?"],
     "The critical section is the part of a process that accesses shared data. A solution must satisfy:\n\n"
     "1. **Mutual exclusion**: only one process in its critical section at a time.\n2. **Progress**: if nobody is "
     "inside, only processes wanting to enter decide who goes next, and the decision is not postponed forever.\n"
     "3. **Bounded waiting**: there is a limit on how many times others enter before a waiting process gets in.\n\n"
     "Without it we get race conditions, for example `counter++` and `counter--` interleaving to give 4 or 6 "
     "instead of 5."),
    ("Critical Section & Peterson's Solution", ["Explain Peterson's solution.", "How does Peterson's algorithm work?"],
     "Peterson's solution is for two processes and uses `flag[2]` and `turn`. Process i does:\n\n"
     "```\nflag[i] = true; turn = j;\nwhile (flag[j] && turn == j) ;   // wait\n// critical section\nflag[i] = false;\n```\n\n"
     "- Mutual exclusion: both could only be inside if `turn` were both i and j at once.\n- Progress: a process that "
     "is not interested has its flag false, so it never blocks the other.\n- Bounded waiting: when j wants to "
     "re-enter it sets `turn = i`, so i gets in after at most one entry by j.\n\nOn modern CPUs that reorder memory "
     "operations it needs memory barriers."),
    ("Mutex Locks & Semaphores", ["What is a semaphore?", "wait and signal operations?", "Binary vs counting semaphore?"],
     "A semaphore S is an integer used only through two atomic operations:\n\n"
     "- `wait(S)` (P): wait while S ≤ 0, then S--.\n- `signal(S)` (V): S++.\n\nA **counting** semaphore can take any "
     "value, for example the number of free buffer slots; a **binary** semaphore is 0 or 1 and works like a mutex. "
     "Without busy waiting, wait() blocks the process on the semaphore's list and signal() wakes one; a value of −k "
     "then means k processes are waiting. Misused, semaphores can cause deadlock and starvation."),
    ("Mutex Locks & Semaphores", ["What is a spinlock?", "Mutex vs semaphore?"],
     "A mutex lock protects a critical section with acquire() and release(). If acquire() busy-waits it is a "
     "**spinlock**: it wastes CPU while waiting but avoids two context switches, so it is good on multiprocessors "
     "when the lock is held briefly.\n\nA mutex has an owner and is either locked or free; a semaphore is a counter "
     "that any process can signal, and a counting semaphore can let several processes in at once."),
    ("Classical Synchronization Problems", ["Solve the bounded-buffer problem with semaphores.", "Producer consumer with semaphores?"],
     "Use three semaphores: `mutex = 1`, `empty = n`, `full = 0`.\n\n"
     "```\nProducer:            Consumer:\nwait(empty);         wait(full);\nwait(mutex);         wait(mutex);\n"
     "add item             remove item\nsignal(mutex);       signal(mutex);\nsignal(full);        signal(empty);\n```\n\n"
     "The order matters: if the producer did `wait(mutex)` before `wait(empty)` on a full buffer, it would hold the "
     "mutex while waiting, the consumer could never enter, and the system would deadlock."),
    ("Classical Synchronization Problems", ["Explain the dining philosophers problem.", "Readers-writers problem?"],
     "**Dining philosophers**: five philosophers, five chopsticks, each needs both neighbours' chopsticks. If all "
     "pick up their left one at the same time, they deadlock. Fixes: allow at most four at the table, pick up both "
     "only if both are free (inside a monitor), or use an asymmetric order.\n\n"
     "**Readers-writers** (first variant): `rw_mutex = 1`, `mutex = 1`, `read_count = 0`. The first reader locks "
     "`rw_mutex` and the last reader releases it, so many readers can read together while a writer gets exclusive "
     "access. Writers can starve if readers keep arriving."),
    # ------------------------------------------------------------------ unit 5
    ("Deadlock Characterization", ["What are the four necessary conditions for deadlock?", "Explain the Coffman conditions."],
     "A deadlock needs all four at the same time:\n\n1. **Mutual exclusion**: at least one resource is not shareable.\n"
     "2. **Hold and wait**: a process holds a resource while waiting for another.\n3. **No preemption**: resources "
     "are only released voluntarily.\n4. **Circular wait**: P0 waits for P1, P1 for P2, ..., Pn for P0.\n\n"
     "Breaking any one of them prevents deadlock; ordering resource types to stop circular wait is the most "
     "practical."),
    ("Deadlock Characterization", ["Does a cycle in a resource allocation graph mean deadlock?", "Explain the resource allocation graph."],
     "In a resource-allocation graph, a request edge Pi → Rj means Pi waits for Rj, and an assignment edge Rj → Pi "
     "means Pi holds an instance of Rj.\n\n- No cycle: no deadlock.\n- Cycle, and every resource has one instance: "
     "deadlock.\n- Cycle, but some resources have several instances: maybe, maybe not.\n\nSo a cycle is necessary "
     "but not sufficient. For single-instance resources the wait-for graph (resources removed) is used for detection."),
    ("Deadlock Prevention & Avoidance (Banker's)", ["What is a safe state?", "Does unsafe mean deadlock?"],
     "A state is safe if there is a **safe sequence**: an order in which every process can get the rest of what it "
     "needs from the free resources plus those released by the processes before it.\n\nA safe state guarantees no "
     "deadlock. An unsafe state does **not** mean a deadlock has happened; it means the OS can no longer guarantee to "
     "avoid one. Banker's algorithm grants a request only if the state after it is still safe."),
    ("Deadlock Prevention & Avoidance (Banker's)", ["Explain the Banker's algorithm.", "Steps of the resource request algorithm?"],
     "Data: Available, Max, Allocation and **Need = Max − Allocation**.\n\n**Safety check**: Work = Available; "
     "repeatedly find an unfinished process with Need ≤ Work, then Work += its Allocation and mark it finished. If "
     "all finish, the state is safe and the finishing order is a safe sequence.\n\n**Request by Pi**: (1) Request ≤ "
     "Need, otherwise it is an error; (2) Request ≤ Available, otherwise Pi waits; (3) pretend to grant it and run the "
     "safety check: grant if safe, otherwise roll back and Pi waits.\n\nIn the classic example with Available "
     "(3, 3, 2), the safe sequence is <P1, P3, P4, P0, P2>, and P1's request (1, 0, 2) is granted."),
    ("Deadlock Detection & Recovery", ["How is a deadlock detected?", "Explain the deadlock detection algorithm."],
     "With one instance per resource type, look for a cycle in the wait-for graph. With several instances, use the "
     "detection algorithm, which is the safety check with **Request** in place of Need:\n\n1. Work = Available; a "
     "process holding nothing is finished.\n2. Find an unfinished process with Request ≤ Work; Work += its "
     "Allocation; repeat.\n3. Every process still unfinished is deadlocked.\n\nRecovery: abort all deadlocked "
     "processes or one at a time, or preempt resources from a victim and roll it back, making sure the same process "
     "is not always chosen."),
    # ------------------------------------------------------------------ unit 6
    ("Memory Management Basics", ["Logical vs physical address?", "What does the MMU do?"],
     "A logical (virtual) address is generated by the CPU; a physical address is what the memory unit sees. With "
     "execution-time binding they differ, and the **MMU** translates every logical address at run time.\n\nWith "
     "relocation and limit registers: if logical < limit, physical = relocation + logical, otherwise the hardware "
     "traps. Example: relocation 14000, limit 3000: logical 346 → 14346; logical 3500 → trap."),
    ("Memory Management Basics", ["Internal vs external fragmentation?"],
     "- **Internal fragmentation**: wasted space inside an allocated block, because the block is bigger than asked "
     "(fixed partitions, the last page of a process in paging).\n- **External fragmentation**: enough free memory in "
     "total, but split into holes too small to use (variable partitions, segmentation).\n\nCompaction or "
     "non-contiguous allocation (paging) solves external fragmentation."),
    ("Contiguous Memory Allocation", ["Compare first fit, best fit and worst fit.", "Which allocation strategy is best?"],
     "- **First fit**: the first hole big enough. Fast.\n- **Best fit**: the smallest hole big enough. Smallest "
     "leftover, but searches the whole list.\n- **Worst fit**: the largest hole. Largest leftover; usually worst.\n- "
     "**Next fit**: like first fit, but resumes where the last search ended.\n\nWith holes 100, 500, 200, 300, 600 KB "
     "and processes 212, 417, 112, 426 KB: the 426 KB process must wait under first fit and worst "
     "fit, while best fit places all four (B4, B2, B3, B5). First fit and best fit beat worst fit; first fit is usually as good "
     "and faster."),
    ("Paging & Segmentation", ["Explain paging.", "How is a logical address translated in paging?"],
     "Physical memory is split into frames and logical memory into pages of the same size; a page table maps each "
     "page to a frame, so a process need not be contiguous.\n\nWith page size 2^n, page number p = address div 2^n "
     "and offset d = address mod 2^n; physical = frame(p) × page size + d. Example: page size 1024, address 3085: "
     "p = 3, d = 13; if page 3 is in frame 9, physical = 9 × 1024 + 13 = 9229.\n\nPaging has no external "
     "fragmentation; the last page wastes on average half a page."),
    ("Paging & Segmentation", ["What is a TLB?", "Calculate effective access time with a TLB."],
     "A TLB is a small, fast associative cache of recent page-table entries, so most translations skip the extra "
     "memory access for the page table.\n\nEAT = h × (TLB + m) + (1 − h) × (TLB + 2m). With m = 100 ns, TLB = 20 ns "
     "and an 80% hit ratio: 0.8 × 120 + 0.2 × 220 = 140 ns."),
    # ------------------------------------------------------------------ unit 7
    ("Demand Paging", ["What is demand paging?", "What happens on a page fault?"],
     "Demand paging loads a page only when it is first used; the valid-invalid bit marks which pages are in "
     "memory.\n\nOn a page fault: the hardware traps; the OS checks the reference is valid; finds a free frame (or a "
     "victim); reads the page from disk; updates the page table; and restarts the instruction.\n\n"
     "EAT = (1 − p) × m + p × fault time. With m = 200 ns, 8 ms service and p = 1/1000, EAT ≈ 8199.8 ns, about 40 "
     "times slower, so the fault rate must be tiny."),
    ("Page Replacement", ["Compare FIFO, LRU and Optimal page replacement.", "Explain page replacement algorithms."],
     "- **FIFO**: replace the page loaded longest ago. Simple, but can throw out busy pages, and shows Belady's "
     "anomaly.\n- **Optimal (OPT)**: replace the page whose next use is furthest in the future. Fewest faults "
     "possible, but needs the future, so it is a benchmark.\n- **LRU**: replace the page whose last use is furthest "
     "in the past. A good approximation of OPT.\n\nOn 7 0 1 2 0 3 0 4 2 3 0 3 2 1 2 0 1 7 0 1 with 3 frames: FIFO 15 "
     "faults, LRU 12, OPT 9."),
    ("Page Replacement", ["What is Belady's anomaly?"],
     "Belady's anomaly is when giving FIFO more frames causes **more** page faults. With 1 2 3 4 1 2 5 1 2 3 4 5, "
     "FIFO gives 9 faults with 3 frames and 10 with 4 frames.\n\nLRU and OPT are stack algorithms: the pages kept "
     "with n frames are always a subset of those kept with n + 1, so they never show the anomaly."),
    ("Thrashing & Working Set", ["What is thrashing?", "How does the working set model prevent thrashing?"],
     "A process thrashes when it spends more time paging than executing, because it doesn't have enough frames for "
     "the pages it is actively using. CPU utilisation drops, the OS adds more processes, and it gets worse.\n\n"
     "The working set WS(Δ) is the set of pages used in the last Δ references. If the total demand D = Σ WSS_i "
     "exceeds the available frames, the OS suspends a process. Page-fault frequency control does the same with upper "
     "and lower bounds on each process's fault rate."),
    # ------------------------------------------------------------------ unit 8
    ("File Systems", ["Compare contiguous, linked and indexed allocation.", "File allocation methods?"],
     "- **Contiguous**: consecutive blocks; fast sequential and direct access, but external fragmentation and hard "
     "to grow.\n- **Linked**: each block points to the next (FAT keeps the links in one table); no external "
     "fragmentation, but direct access is slow and a bad pointer loses the rest of the file.\n- **Indexed**: an "
     "index block lists all the file's blocks (UNIX inode); direct access without external fragmentation, at the cost "
     "of an index block per file.\n\nAn inode with 12 direct, single, double and triple indirect pointers, 4 KB blocks "
     "and 4-byte pointers supports files of about 4 TB."),
    ("File Systems", ["Hard link vs soft link?", "What is an inode?"],
     "An inode stores a file's metadata (owner, permissions, size, timestamps) and pointers to its data blocks; the "
     "directory entry only maps a name to an inode number.\n\nA **hard link** is another name for the same inode: "
     "the file stays until the link count reaches 0, and it cannot cross file systems. A **soft (symbolic) link** is "
     "a small file holding a path; it breaks if the target is deleted."),
    ("Disk Scheduling", ["Compare disk scheduling algorithms.", "SCAN vs C-SCAN vs LOOK?"],
     "- **FCFS**: arrival order; fair but lots of head movement.\n- **SSTF**: always the closest request; less "
     "movement but far requests can starve.\n- **SCAN**: sweep to the disk edge, then reverse.\n- **C-SCAN**: sweep "
     "to the edge, jump to the other end, continue the same way; more uniform waits.\n- **LOOK / C-LOOK**: like SCAN "
     "/ C-SCAN but turn at the last request.\n\nFor 98, 183, 37, 122, 14, 124, 65, 67 with the head at 53 (0–199): "
     "FCFS 640, SSTF 236, C-SCAN upwards 382 (counting the return jump), C-LOOK upwards 322."),
    # ------------------------------------------------------------------ unit 9
    ("Linux Commands", ["What does chmod 754 mean?", "Explain Linux file permissions."],
     "Permissions are read (4), write (2) and execute (1) for the owner, the group and others, in that order.\n\n"
     "`chmod 754 file` gives the owner 7 = rwx, the group 5 = r-x and others 4 = r--, shown by `ls -l` as "
     "`-rwxr-xr--`. The symbolic form does the same with letters, for example `chmod u+x file` or `chmod go-w file`."),
    ("Linux Commands", ["Explain pipes and redirection in Linux.", "Difference between > and >>?"],
     "- `cmd > file` writes standard output to a file, replacing it; `>>` appends.\n- `cmd < file` reads input from "
     "a file; `2>` redirects errors; `> file 2>&1` sends both.\n- `cmd1 | cmd2` connects the output of cmd1 to the "
     "input of cmd2. Each command is its own process, joined by a pipe made with the pipe() system call.\n\n"
     "Example: `ps aux | grep firefox` lists processes and keeps only the lines mentioning firefox."),
    ("Linux Commands", ["kill vs kill -9?", "How do you manage processes in Linux?"],
     "`ps aux` or `ps -ef` lists processes; `top` shows them live. `kill PID` sends SIGTERM, which a process can "
     "catch to clean up; `kill -9 PID` sends SIGKILL, which cannot be caught or ignored.\n\n`command &` runs in the "
     "background, `jobs` lists jobs, `fg` and `bg` move them, Ctrl+Z suspends and Ctrl+C interrupts. `nice` and "
     "`renice` change priority (−20 highest, 19 lowest)."),
]

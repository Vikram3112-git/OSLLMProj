# Processes, Threads and Inter-process Communication

## Process concept
A program is a passive file on disk; a process is a program in execution, with its own state. A process in memory has:
- Text section: the program code.
- Data section: global and static variables.
- Heap: memory allocated at run time (malloc, new); it grows upwards.
- Stack: function parameters, return addresses and local variables; it grows downwards.

## Process states
- New: the process is being created.
- Ready: waiting to be assigned the CPU.
- Running: instructions are being executed.
- Waiting (blocked): waiting for an event such as I/O completion.
- Terminated: finished execution.
Transitions: new → ready (admitted), ready → running (scheduler dispatch), running → ready (interrupt or time slice over), running → waiting (I/O or event wait), waiting → ready (I/O or event completion), running → terminated (exit).

## Process control block (PCB)
The kernel keeps one PCB per process: process state, process ID, program counter, CPU registers, CPU-scheduling information (priority, queue pointers), memory-management information (base and limit registers, page tables), accounting information (CPU time used), and I/O status (open files, devices).

## Context switch
When the CPU switches from one process to another, the kernel saves the state of the old process in its PCB and loads the saved state of the new one. A context switch is pure overhead: no useful work is done during it. Its time depends on the hardware (number of registers, special instructions).

## Operations on processes
- Creation: a parent process creates children, forming a tree of processes (on Linux the root is systemd, PID 1). On UNIX, fork() creates a child that is a copy of the parent; exec() replaces the child's memory with a new program; the parent can call wait() to wait for the child to finish.
- fork() returns 0 in the child, the child's PID in the parent, and -1 if it fails.
- After n fork() calls in sequence (each executed by every existing process), there are 2^n processes in total, that is 2^n − 1 new processes. Example: three fork() calls give 8 processes.
- Termination: a process calls exit(); the OS frees its resources and reports the exit status to the parent through wait().
- Zombie: a child that has terminated but whose parent has not yet called wait(); its PCB entry stays so the parent can read the status.
- Orphan: a child whose parent terminated first; it is adopted by init/systemd, which waits for it.

Modern systems use copy-on-write after fork(): parent and child share pages until one of them writes, so fork() followed by exec() is cheap. Chrome runs each tab in a separate process so one crashing tab does not bring down the browser. Android ranks processes by importance (foreground, visible, service, background, empty) and kills the least important when memory is short.

## Threads
A thread is a basic unit of CPU use inside a process. Threads of the same process share the code, data and open files, but each thread has its own thread ID, program counter, registers and stack.

Benefits: responsiveness (one thread can keep the interface working while another blocks), resource sharing, economy (creating a thread and switching between threads is cheaper than for processes), and scalability on multicore CPUs.

User-level threads are managed by a library without kernel support; kernel-level threads are managed by the OS.

Multithreading models:
- Many-to-one: many user threads on one kernel thread. Cheap, but one blocking system call blocks all threads and they cannot run in parallel on multiple cores.
- One-to-one: each user thread maps to a kernel thread (Linux, Windows). True parallelism; creating many threads costs more.
- Many-to-many: many user threads multiplexed on a smaller or equal number of kernel threads; combines the advantages.

Concurrency means several tasks make progress (possibly by interleaving on one core); parallelism means several tasks run at the same instant on different cores.

Amdahl's law: speedup ≤ 1 / (S + (1 − S) / N), where S is the serial fraction and N the number of cores. Example: with S = 0.25, two cores give at most 1 / (0.25 + 0.375) = 1.6 times speedup, and four cores 1 / (0.25 + 0.1875) ≈ 2.29 times.

Thread libraries: POSIX Pthreads (pthread_create, pthread_join), Windows threads, Java threads. Implicit threading: thread pools, fork-join, OpenMP.

## Inter-process communication (IPC)
Processes are independent (they do not share data) or cooperating. Cooperating processes need IPC. There are two models:
- Shared memory: the processes share a region of memory and read and write it directly. Fast after setup, because no system call is needed for each access, but the processes must synchronize themselves.
- Message passing: processes exchange messages through the kernel with send() and receive(). Easier to use, no conflicts to manage, and works across machines, but each message costs a system call.

## Producer-consumer problem (bounded buffer, shared memory)
A producer creates items and a consumer uses them through a shared circular buffer of size BUFFER_SIZE with two indices: in (next free slot) and out (first full slot).
- Buffer empty: in == out.
- Buffer full: ((in + 1) % BUFFER_SIZE) == out.
- Producer: while full, wait; buffer[in] = item; in = (in + 1) % BUFFER_SIZE.
- Consumer: while empty, wait; item = buffer[out]; out = (out + 1) % BUFFER_SIZE.
With this scheme the buffer holds at most BUFFER_SIZE − 1 items. If a shared counter is used instead, counter++ and counter-- can race, which is why synchronization is needed.

## Message passing details
- Direct communication: processes name each other, send(P, message) and receive(Q, message); a link connects exactly one pair.
- Indirect communication: messages go through mailboxes (ports); a link can be shared by several processes.
- Synchronization: blocking (synchronous) send and receive, or non-blocking (asynchronous). Blocking send plus blocking receive is called a rendezvous.
- Buffering: zero capacity (sender must wait for receiver), bounded capacity, unbounded capacity.
- Pipes on UNIX: an ordinary pipe (pipe()) is one-way and used between a parent and child; a named pipe (FIFO) has a name in the file system and can be used by unrelated processes.

## Common mistakes
- Thinking threads of a process have separate data sections. They share them; only the stack and registers are private.
- Counting fork() processes as n + 1 instead of 2^n.
- Saying the circular buffer holds BUFFER_SIZE items; with in/out pointers it holds BUFFER_SIZE − 1.

## Viva questions
- What is stored in a PCB? State, PID, program counter, registers, scheduling, memory and accounting information, open files.
- Difference between a zombie and an orphan? A zombie has finished but is not yet waited for; an orphan is still running but its parent has finished.
- Why are threads cheaper than processes? They share the address space and resources, so creation and switching need less work.
- Shared memory or message passing for large data on one machine? Shared memory, because data is not copied through the kernel for each access.

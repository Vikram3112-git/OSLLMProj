# Process Scheduling Fundamentals

## Why CPU scheduling is needed
In a multiprogrammed system several processes are kept in memory at the same time. When the running process has to wait (usually for I/O), the operating system takes the CPU away from it and gives it to another process. The goal is to keep the CPU busy as much as possible. Choosing which ready process gets the CPU next is called CPU scheduling or process scheduling.

## CPU burst and I/O burst cycle
Process execution alternates between CPU bursts (computing) and I/O bursts (waiting for devices). A process starts and ends with a CPU burst. Most CPU bursts are short and only a few are long. An I/O-bound process has many short CPU bursts, while a CPU-bound process has a few long CPU bursts. This distribution matters when choosing a scheduling algorithm.

## Process states and queues
A process moves between the states new, ready, running, waiting (blocked) and terminated. Processes that are in memory and ready to run wait in the ready queue. Processes waiting for an I/O device wait in a device queue. The scheduler selects processes only from the ready queue.

## Types of schedulers
- Long-term scheduler (job scheduler): decides which jobs are admitted into memory. It controls the degree of multiprogramming and runs infrequently.
- Short-term scheduler (CPU scheduler): selects which ready process runs next on the CPU. It runs very often (every few milliseconds), so it must be fast.
- Medium-term scheduler: swaps processes out of memory and later back in, to reduce the degree of multiprogramming or improve the process mix.

## Dispatcher
The dispatcher is the module that gives control of the CPU to the process selected by the short-term scheduler. It performs the context switch, switches to user mode, and jumps to the proper location in the user program. The time it takes to stop one process and start another is called dispatch latency. A context switch saves the state (PCB) of the old process and loads the saved state of the new one. Context-switch time is pure overhead because no useful work is done during it.

## When scheduling decisions happen
Scheduling decisions can take place when a process:
1. switches from running to waiting (for example, an I/O request),
2. switches from running to ready (for example, a timer interrupt),
3. switches from waiting to ready (for example, I/O completion),
4. terminates.

If scheduling happens only in cases 1 and 4, the scheme is non-preemptive (cooperative): once a process has the CPU it keeps it until it blocks or terminates. If scheduling can also happen in cases 2 and 3, the scheme is preemptive: the OS can take the CPU away from a running process.

## Preemptive vs non-preemptive
Non-preemptive scheduling is simple and has low overhead, but a long process can hold the CPU and make short or interactive processes wait. Preemptive scheduling gives better response time for interactive systems, but costs extra context switches and can cause race conditions on shared data, which needs synchronisation. FCFS, SJF and non-preemptive Priority are non-preemptive. SRTF, preemptive Priority and Round Robin are preemptive.

## Thread scheduling
On systems that support threads, the kernel schedules kernel-level threads, not processes. With process-contention scope (PCS), the thread library schedules user threads onto available LWPs, and competition is among threads of the same process. With system-contention scope (SCS), the kernel decides which kernel thread runs, and competition is among all threads in the system.

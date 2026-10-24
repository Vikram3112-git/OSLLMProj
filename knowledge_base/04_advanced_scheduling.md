# Multilevel, Multiprocessor and Real-Time Scheduling

## Multilevel Queue Scheduling
The ready queue is split into several separate queues, for example foreground (interactive) and background (batch). Each process is permanently assigned to one queue based on a property such as process type or memory size. Each queue has its own algorithm, for example RR for foreground and FCFS for background. Scheduling between queues is usually fixed-priority preemptive (background runs only when foreground is empty, which risks starvation) or time-sliced (for example, 80% of CPU time to foreground and 20% to background). A typical order from highest priority is: system processes, interactive processes, interactive editing processes, batch processes, student processes.

## Multilevel Feedback Queue (MLFQ)
Like a multilevel queue, but processes can move between queues. A process that uses too much CPU time is moved to a lower-priority queue, so I/O-bound and interactive processes stay in the higher queues. A process that waits too long in a low queue can be moved up, which is aging and prevents starvation. Example: queue 0 is RR with q = 8, queue 1 is RR with q = 16, queue 2 is FCFS. A new process enters queue 0. If it does not finish within 8 ms it moves to queue 1, and if it still does not finish within 16 more ms it moves to queue 2. An MLFQ is defined by the number of queues, the algorithm for each queue, the rules for upgrading and demoting processes, and the rule for which queue a new process enters. It is the most general scheme but also the most complex to configure.

## Multiprocessor Scheduling
- Asymmetric multiprocessing: one master processor makes all scheduling decisions and the others run only user code. This is simple because only one processor accesses system data structures.
- Symmetric multiprocessing (SMP): each processor schedules itself, from a common ready queue or from a private per-processor queue.
- Processor affinity: a process tends to stay on the processor where it has been running, because that processor's cache already holds its data. Soft affinity is a preference; hard affinity is a guarantee.
- Load balancing: keeps the workload evenly spread. With push migration, a task periodically moves processes from overloaded processors to idle ones. With pull migration, an idle processor pulls a waiting task from a busy one. Load balancing works against processor affinity.
- Multicore and hardware threads: when a core stalls on a memory access, it can switch to another hardware thread, so scheduling happens at two levels.

## Real-Time Scheduling
- Soft real-time systems give critical tasks preference but do not guarantee deadlines. Hard real-time systems must meet deadlines.
- Real-time processes are often periodic, with processing time t, deadline d and period p, where 0 ≤ t ≤ d ≤ p.
- Rate-Monotonic Scheduling: static priorities, where a shorter period gets a higher priority. It is optimal among static-priority schemes. CPU utilisation is bounded by N(2^(1/N) − 1), about 69% for large N.
- Earliest Deadline First (EDF): dynamic priorities, where the earlier deadline gets the higher priority. In theory it can reach 100% CPU utilisation.
- Real-time scheduling needs preemptive, priority-based scheduling and low interrupt and dispatch latency.

## Examples from real operating systems
- Linux uses the Completely Fair Scheduler (CFS), which tracks each task's virtual runtime and runs the task with the smallest virtual runtime, stored in a red-black tree. Nice values weight how fast virtual runtime grows. Linux also has real-time classes (SCHED_FIFO and SCHED_RR) with higher priority than normal tasks.
- Windows uses a preemptive, priority-based scheduler with 32 priority levels. The highest-priority ready thread runs, and interactive threads get priority boosts.

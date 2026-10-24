# CPU Scheduling Algorithms

Course conventions: a lower priority number means higher priority. Ties are broken by earlier arrival time, then by lower process number. In Round Robin, a process arriving at the same moment a quantum expires joins the ready queue before the preempted process.

## First-Come, First-Served (FCFS)
The process that requests the CPU first gets it first. It is implemented with a FIFO queue and is non-preemptive. It is simple, but the average waiting time is often long and depends heavily on arrival order.

Convoy effect: when one long CPU-bound process holds the CPU, many short I/O-bound processes wait behind it, like cars stuck behind a slow truck. Both CPU and device utilisation drop. FCFS is unsuitable for time-sharing systems.

Worked example (FCFS): P1 (AT 0, BT 5), P2 (AT 1, BT 3), P3 (AT 2, BT 8), P4 (AT 3, BT 6).
Gantt chart: P1 [0-5] | P2 [5-8] | P3 [8-16] | P4 [16-22].
CT: P1 = 5, P2 = 8, P3 = 16, P4 = 22. TAT: 5, 7, 14, 19. WT: 0, 4, 6, 13.
Average TAT = 11.25, Average WT = 5.75.

## Shortest Job First (SJF), non-preemptive
When the CPU becomes free, it is given to the arrived process with the smallest next CPU burst. SJF is provably optimal: it gives the minimum average waiting time for a given set of processes, because moving a short process before a long one reduces the short one's wait more than it increases the long one's wait. Its difficulty is that the length of the next CPU burst is not known in advance. It is predicted with exponential averaging: τ(n+1) = α·t(n) + (1 − α)·τ(n), where t(n) is the actual length of the nth burst, τ(n) is the past prediction, and 0 ≤ α ≤ 1 (commonly α = 1/2). Long processes can starve if short ones keep arriving.

Key rule: choose only among processes that have already arrived. A short job that has not arrived yet cannot be chosen.

Worked example (SJF): P1 (AT 0, BT 7), P2 (AT 2, BT 4), P3 (AT 4, BT 1), P4 (AT 5, BT 4).
At time 0 only P1 has arrived, so it runs to completion: P1 [0-7]. At 7, P2, P3 and P4 are ready, so P3 (BT 1) runs: P3 [7-8]. P2 and P4 tie at BT 4, and P2 arrived first: P2 [8-12], then P4 [12-16].
CT: P1 = 7, P2 = 12, P3 = 8, P4 = 16. TAT: 7, 10, 4, 11. WT: 0, 6, 3, 7.
Average TAT = 8.00, Average WT = 4.00.

## Shortest Remaining Time First (SRTF), preemptive SJF
Whenever a new process arrives, the scheduler compares its burst with the remaining time of the running process. If the new process needs less time, the running process is preempted. SRTF gives a lower average waiting time than non-preemptive SJF but causes more context switches.

Worked example (SRTF) with the same processes: P1 (0, 7), P2 (2, 4), P3 (4, 1), P4 (5, 4).
P1 runs 0-2. At 2, P2 (4) < P1 remaining (5), so P2 preempts and runs 2-4. At 4, P3 (1) < P2 remaining (2), so P3 runs 4-5. At 5, P2 remaining 2 is the smallest, so P2 runs 5-7. Then P4 (4) < P1 (5), so P4 runs 7-11. Finally P1 runs 11-16.
Gantt chart: P1 [0-2] | P2 [2-4] | P3 [4-5] | P2 [5-7] | P4 [7-11] | P1 [11-16].
CT: P1 = 16, P2 = 7, P3 = 5, P4 = 11. TAT: 16, 5, 1, 6. WT: 9, 1, 0, 2.
Average TAT = 7.00, Average WT = 3.00. Note that P1's waiting time (9) is the sum of all the time it spent preempted.

## Priority Scheduling
Each process has a priority and the CPU goes to the highest-priority ready process (lowest number, in this course). SJF is a special case where the priority is the predicted next burst. Priority scheduling can be non-preemptive or preemptive. In the preemptive version, a newly arrived process with higher priority preempts the running one.

Starvation (indefinite blocking): low-priority processes may never run if higher-priority ones keep arriving. Aging solves this by gradually increasing the priority of processes that wait a long time.

Worked example (non-preemptive priority): P1 (AT 0, BT 4, Pr 3), P2 (AT 1, BT 3, Pr 1), P3 (AT 2, BT 2, Pr 4), P4 (AT 3, BT 5, Pr 2).
Gantt chart: P1 [0-4] | P2 [4-7] | P4 [7-12] | P3 [12-14]. WT: P1 0, P2 3, P3 10, P4 4. Average WT = 4.25, Average TAT = 7.75.

Same processes, preemptive priority: P2 arrives at 1 with higher priority and preempts P1.
Gantt chart: P1 [0-1] | P2 [1-4] | P4 [4-9] | P1 [9-12] | P3 [12-14]. WT: P1 8, P2 0, P3 10, P4 1. Average WT = 4.75, Average TAT = 8.25.

## Round Robin (RR)
Designed for time-sharing. The ready queue is a circular FIFO queue. Each process gets the CPU for at most one time quantum q. If it has not finished when the quantum expires, it is preempted and put at the tail of the ready queue. If its burst is shorter than q, it releases the CPU voluntarily. With n processes, no process waits more than (n − 1)·q before its next quantum, so response time is good.

Choosing the quantum: if q is very large, RR becomes FCFS. If q is very small, there are too many context switches and overhead dominates. A rule of thumb is that about 80% of CPU bursts should be shorter than q. q must also be large compared to the context-switch time. Average turnaround time does not necessarily improve as q increases.

Worked example (RR, q = 2): P1 (AT 0, BT 5), P2 (AT 1, BT 4), P3 (AT 2, BT 2), P4 (AT 4, BT 1).
P1 runs 0-2. P2 (arrived 1) and P3 (arrived 2) join before the preempted P1, so the queue is P2, P3, P1. P2 runs 2-4; P4 arrives at 4 and joins before P2, so the queue is P3, P1, P4, P2. P3 runs 4-6 and finishes. P1 runs 6-8, P4 runs 8-9 and finishes, P2 runs 9-11 and finishes, P1 runs 11-12 and finishes.
Gantt chart: P1 [0-2] | P2 [2-4] | P3 [4-6] | P1 [6-8] | P4 [8-9] | P2 [9-11] | P1 [11-12].
CT: P1 = 12, P2 = 11, P3 = 6, P4 = 9. TAT: 12, 10, 4, 5. WT: 7, 6, 2, 4.
Average TAT = 7.75, Average WT = 4.75.

## Comparison summary
- FCFS: simple, non-preemptive, convoy effect, poor for interactive use.
- SJF: optimal average waiting time, needs burst prediction, long jobs can starve.
- SRTF: preemptive SJF, even lower average waiting time, more context switches.
- Priority: flexible, risk of starvation, fixed by aging.
- Round Robin: fair, good response time, performance depends on the quantum, higher average turnaround than SJF.

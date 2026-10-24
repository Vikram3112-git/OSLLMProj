# How to Create a Gantt Chart and Solve a Scheduling Problem

## What a Gantt chart is
A Gantt chart for CPU scheduling is a horizontal timeline that shows which process is using the CPU during each interval of time. Each box is labelled with a process name, and the time at each box boundary is written underneath. Example:
| P1 | P2 | P3 |
0    5    8    16
This means P1 ran from 0 to 5, P2 from 5 to 8 and P3 from 8 to 16. If no process is ready, the CPU is idle and the box is labelled IDLE.

## The general method (works for every algorithm)
1. Write the process table: process, arrival time (AT), burst time (BT), and priority if given.
2. Start the clock at the earliest arrival time.
3. At every decision point, list the ready queue: all processes that have arrived (AT ≤ current time) and are not finished.
4. Apply the algorithm's rule to pick one process from the ready queue.
5. Decide how long it runs. In non-preemptive algorithms it runs until it finishes. In preemptive algorithms it runs until it finishes OR until a new arrival might preempt it. In Round Robin it runs for at most one time quantum.
6. Draw that box on the timeline, move the clock forward, and repeat from step 3 until every process is finished.
7. If the ready queue is empty, draw an IDLE box until the next arrival.

## Decision points for each algorithm
- FCFS: pick the earliest arrival. Decision points are only when a process finishes.
- SJF (non-preemptive): pick the smallest burst time among processes that have ALREADY arrived. Decide only when a process finishes.
- SRTF: pick the smallest remaining time. Re-check at every arrival and at every completion, because a new short process can preempt the running one.
- Priority non-preemptive: pick the highest priority (lowest number) among arrived processes when the CPU becomes free.
- Priority preemptive: same rule, but re-check at every arrival; a higher-priority arrival preempts the running process.
- Round Robin: take the process at the front of the ready queue and run it for at most q units. If it is not finished, put it at the back of the queue, after any processes that arrived during its quantum.

## Solving: from the Gantt chart to the answers
1. Completion Time (CT): the time at the right edge of the LAST box of that process.
2. Turnaround Time: TAT = CT − AT.
3. Waiting Time: WT = TAT − BT. This automatically counts every period the process spent waiting, including after preemptions.
4. Response Time: RT = (start of the FIRST box of that process) − AT.
5. Averages: add the column and divide by the number of processes.
6. Check your work: the sum of all burst times plus idle time must equal the total length of the Gantt chart, and no WT can be negative.

## Worked example (FCFS)
Processes: P1 (AT 0, BT 4), P2 (AT 1, BT 3), P3 (AT 2, BT 1).
At t=0 only P1 is ready, so P1 runs 0 to 4. At t=4 P2 and P3 are waiting; P2 arrived first, so P2 runs 4 to 7. Then P3 runs 7 to 8.
Gantt chart: | P1 | P2 | P3 | with times 0, 4, 7, 8.
CT: P1 = 4, P2 = 7, P3 = 8. TAT: 4 − 0 = 4, 7 − 1 = 6, 8 − 2 = 6. WT: 4 − 4 = 0, 6 − 3 = 3, 6 − 1 = 5.
Average TAT = 16 / 3 = 5.33. Average WT = 8 / 3 = 2.67.
Notice that P3 needed only 1 unit but waited 5. This is the convoy effect, and it is exactly why SJF was invented: with SJF, P3 would run at t=4 and wait only 2.

## Typical exam mistakes when drawing Gantt charts
- Choosing a process that has not arrived yet (for example, picking the shortest job in SJF even though it arrives later).
- Forgetting to re-check for preemption at every arrival in SRTF and preemptive Priority.
- In Round Robin, putting the preempted process back in the queue before the processes that arrived during its quantum.
- Forgetting idle time when no process has arrived.
- Reading the start of a box as the completion time.

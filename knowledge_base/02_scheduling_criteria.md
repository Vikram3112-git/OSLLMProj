# Scheduling Criteria and Performance Measures

## Criteria used to compare algorithms
- CPU utilisation: the percentage of time the CPU is busy. Should be maximised.
- Throughput: the number of processes completed per unit time. Should be maximised.
- Turnaround time: the total time from submission (arrival) to completion of a process. Should be minimised.
- Waiting time: the total time a process spends waiting in the ready queue. The scheduling algorithm directly affects only this. Should be minimised.
- Response time: the time from submission until the process first gets the CPU (first response). Important for interactive systems. Should be minimised.

Usually we optimise the average value. For interactive systems it can be more important to minimise the variance of response time than the average.

## Formulas (course convention)
- Arrival Time (AT): when the process enters the ready queue.
- Burst Time (BT): the CPU time the process needs.
- Completion Time (CT): when the process finishes, read from the Gantt chart.
- Turnaround Time: TAT = CT − AT
- Waiting Time: WT = TAT − BT
- Response Time: RT = (time the process first gets the CPU) − AT
- Average TAT = sum of all TAT ÷ number of processes. Average WT is found the same way.
- Throughput = number of processes ÷ total time span of the schedule.
- CPU utilisation = time the CPU is busy ÷ total time span × 100%.

## Common mistakes
- Writing TAT = CT and forgetting to subtract the arrival time. TAT = CT only when AT = 0.
- Writing WT = CT − BT. This is only correct when AT = 0. Always compute WT = TAT − BT.
- In preemptive algorithms, WT is not just "start time − arrival time". A preempted process waits again every time it is taken off the CPU, and WT = TAT − BT counts all of these waits. Start time − arrival time is the response time.
- Forgetting idle time. If no process has arrived, the CPU is idle. Show it as IDLE in the Gantt chart and do not count it as waiting for any process.
- Dividing by the wrong number of processes when averaging.

## Gantt chart
A Gantt chart is a bar showing which process runs in each time interval, with the times written below the boundaries. Example: | P1 | P2 | P3 | with times 0, 5, 8, 16. The completion time of a process is the end of its last bar.

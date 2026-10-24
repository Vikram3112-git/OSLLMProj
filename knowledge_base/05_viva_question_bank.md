# Process Scheduling Viva and Exam Question Bank

Q: Differentiate between preemptive and non-preemptive scheduling.
A: In non-preemptive scheduling, a running process keeps the CPU until it terminates or blocks for I/O. In preemptive scheduling, the OS can take the CPU away, for example on a timer interrupt or when a higher-priority process arrives. Preemptive scheduling improves responsiveness but adds context-switch overhead and needs synchronisation for shared data.

Q: What is the difference between the scheduler and the dispatcher?
A: The short-term scheduler decides which ready process runs next. The dispatcher carries out that decision: it switches context, switches to user mode, and jumps to the right instruction. Dispatch latency is the dispatcher's overhead.

Q: Why is SJF called optimal, and why is it hard to implement?
A: For a given set of processes it gives the minimum average waiting time, because running shorter jobs first reduces total waiting. It is hard to implement because the next CPU burst length is unknown, so it must be predicted, for example by exponential averaging.

Q: What is the convoy effect?
A: In FCFS, short processes stuck behind one long process all wait, which lowers CPU and I/O device utilisation.

Q: What is starvation and how is it solved?
A: Starvation is when a low-priority process waits indefinitely because higher-priority processes keep getting the CPU. Aging solves it by gradually raising the priority of processes that have waited a long time.

Q: How does the time quantum affect Round Robin?
A: A very large quantum makes RR behave like FCFS. A very small quantum causes too many context switches and high overhead. The quantum should be large compared to the context-switch time, and about 80% of CPU bursts should finish within one quantum.

Q: What is the difference between turnaround time, waiting time and response time?
A: Turnaround time is completion minus arrival (the total time in the system). Waiting time is the total time spent in the ready queue (TAT − BT). Response time is the time until the process first gets the CPU.

Q: Which algorithms can cause starvation?
A: SJF, SRTF and Priority scheduling (and fixed-priority multilevel queues). FCFS and Round Robin do not cause starvation.

Q: How is a multilevel feedback queue different from a multilevel queue?
A: In a multilevel queue, processes are permanently assigned to one queue. In a multilevel feedback queue, processes move between queues based on their CPU usage, and aging moves long-waiting processes up.

Q: What is processor affinity?
A: It is the tendency to keep a process on the same processor to reuse its warm cache. Soft affinity is a preference and hard affinity is a strict binding. Load balancing can conflict with it.

Q: Is SRTF always better than SJF?
A: It gives an equal or lower average waiting time, but it causes more context switches, needs burst-length prediction, and can starve long processes more severely.

Q: What is a CPU-bound process versus an I/O-bound process?
A: A CPU-bound process spends most of its time computing and has long CPU bursts. An I/O-bound process does a lot of I/O and has many short CPU bursts. A good scheduler mixes both to keep the CPU and the devices busy.

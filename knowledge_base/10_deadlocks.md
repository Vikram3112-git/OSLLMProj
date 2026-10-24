# Deadlocks

## System model and definition
Processes use resources (CPU cycles, memory, files, I/O devices, locks) in the order request → use → release. A set of processes is deadlocked when every process in the set is waiting for an event (usually the release of a resource) that only another process in the set can cause.

## Necessary conditions (all four must hold at the same time)
1. Mutual exclusion: at least one resource is non-shareable.
2. Hold and wait: a process holds at least one resource while waiting for more.
3. No preemption: a resource can only be released voluntarily by the process holding it.
4. Circular wait: there is a chain P0 → P1 → ... → Pn → P0 where each process waits for a resource held by the next.

## Resource-allocation graph (RAG)
Vertices are processes (circles) and resource types (rectangles, with a dot for each instance). A request edge Pi → Rj means Pi is waiting for Rj; an assignment edge Rj → Pi means an instance of Rj is held by Pi.
- No cycle: no deadlock.
- Cycle and every resource has a single instance: deadlock.
- Cycle and some resources have several instances: there may or may not be a deadlock. A cycle is necessary but not sufficient.
A wait-for graph is obtained by removing the resource nodes and joining Pi → Pj when Pi waits for a resource held by Pj. With single-instance resources, a cycle in the wait-for graph means deadlock.

## Methods for handling deadlocks
Prevention, avoidance, detection and recovery, or ignoring the problem (the "ostrich algorithm", used by most general-purpose systems because deadlocks are rare and the other methods are expensive).

## Deadlock prevention (make one condition impossible)
- Mutual exclusion: cannot be removed for non-shareable resources such as printers or locks.
- Hold and wait: request all resources at once before starting, or only when holding none. Low resource utilisation and possible starvation.
- No preemption: if a process holding resources requests one that is not available, it releases everything it holds. Works for resources whose state can be saved (CPU registers, memory), not for printers or locks.
- Circular wait: number all resource types and require requests in increasing order. This is the most practical method.

## Deadlock avoidance: safe states and Banker's algorithm
The OS needs to know in advance the maximum demand of each process. A state is safe if there is a safe sequence <P1, P2, ..., Pn> in which every process can get the resources it still needs from the free resources plus those released by the processes before it. A safe state means no deadlock. An unsafe state does not mean a deadlock has happened; it means the OS can no longer guarantee to avoid one.

Banker's algorithm data structures (n processes, m resource types):
- Available[m]: free instances of each type.
- Max[n][m]: maximum demand of each process.
- Allocation[n][m]: instances currently held.
- Need[n][m] = Max − Allocation.

Safety algorithm (course convention: repeated passes over P0..Pn−1 in order):
1. Work = Available; Finish[i] = false for all i.
2. Find an i with Finish[i] = false and Need[i] ≤ Work (every component).
3. Work = Work + Allocation[i]; Finish[i] = true; go to step 2.
4. If every Finish[i] is true, the state is safe. Any order that passes the check is a valid safe sequence.

Resource-request algorithm for a request by Pi:
1. If Request ≤ Need[i], continue; otherwise it is an error (the process exceeded its maximum claim).
2. If Request ≤ Available, continue; otherwise Pi must wait.
3. Pretend to grant it: Available −= Request, Allocation[i] += Request, Need[i] −= Request. Run the safety algorithm; grant the request only if the new state is safe, otherwise restore the old state and Pi waits.

## Worked example (solved exactly by OSLLM's solver)
Five processes, resource types A, B, C, Available (3, 3, 2).

| Process | Allocation | Max | Need |
|---|---|---|---|
| P0 | 0 1 0 | 7 5 3 | 7 4 3 |
| P1 | 2 0 0 | 3 2 2 | 1 2 2 |
| P2 | 3 0 2 | 9 0 2 | 6 0 0 |
| P3 | 2 1 1 | 2 2 2 | 0 1 1 |
| P4 | 0 0 2 | 4 3 3 | 4 3 1 |

Pass 1: P0 needs (7, 4, 3) > Work (3, 3, 2), so it waits. P1 needs (1, 2, 2) ≤ (3, 3, 2): it finishes and Work becomes (5, 3, 2). P2 needs (6, 0, 0) > (5, 3, 2): waits. P3 needs (0, 1, 1) ≤ (5, 3, 2): Work becomes (7, 4, 3). P4 needs (4, 3, 1) ≤ (7, 4, 3): Work becomes (7, 4, 5).
Pass 2: P0 needs (7, 4, 3) ≤ (7, 4, 5): Work becomes (7, 5, 5). P2 needs (6, 0, 0) ≤ (7, 5, 5): Work becomes (10, 5, 7).
The state is safe with safe sequence <P1, P3, P4, P0, P2>. (Other orders, such as <P1, P3, P4, P2, P0>, are also valid.)

Request (1, 0, 2) by P1: (1, 0, 2) ≤ Need (1, 2, 2) and ≤ Available (3, 3, 2). After pretending, Available = (2, 3, 0) and the safety check still succeeds with <P1, P3, P4, P0, P2>, so the request is granted. In that new state a request (3, 3, 0) by P4 must wait (not enough available), and a request (0, 2, 0) by P0 is refused because the resulting state would be unsafe.

## Deadlock detection
For single-instance resources, look for a cycle in the wait-for graph. For several instances, use the detection algorithm, which is like the safety algorithm with Request instead of Need:
1. Work = Available; Finish[i] = true if Allocation[i] is all zero, otherwise false.
2. Find i with Finish[i] = false and Request[i] ≤ Work; set Work += Allocation[i], Finish[i] = true; repeat.
3. Every process with Finish[i] = false at the end is deadlocked.
Example: with Allocation P0 (0,1,0), P1 (2,0,0), P2 (3,0,3), P3 (2,1,1), P4 (0,0,2), Request P0 (0,0,0), P1 (2,0,2), P2 (0,0,0), P3 (1,0,0), P4 (0,0,2) and Available (0,0,0), there is no deadlock (order <P0, P2, P3, P4, P1>). If P2 now requests one more C, P1, P2, P3 and P4 are deadlocked.

How often to run detection: every time a request cannot be granted (expensive) or at intervals, for example once an hour or when CPU utilisation drops below 40%.

## Recovery
- Process termination: abort all deadlocked processes (simple but costly), or abort one at a time until the cycle is broken, choosing the victim by priority, time already used, resources held and how many more it needs.
- Resource preemption: select a victim, roll it back to a safe state (or restart it), and make sure the same process is not always the victim (starvation), for example by counting rollbacks in the cost.

## Common mistakes
- Saying unsafe means deadlocked.
- Forgetting to check Request ≤ Need before Request ≤ Available.
- Using Max instead of Need in the safety check.
- Thinking a cycle always means deadlock when resources have several instances.

## Viva questions
- Which prevention method is most practical? Ordering resources to prevent circular wait.
- Why is Banker's algorithm rarely used in general-purpose OSs? Processes rarely know their maximum needs and the check costs O(m × n²) for every request.
- Difference between avoidance and detection? Avoidance never enters an unsafe state; detection lets deadlocks happen and then finds and breaks them.

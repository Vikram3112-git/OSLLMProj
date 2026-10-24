# Process Synchronization

## Race condition
When several processes or threads access shared data at the same time and the result depends on the order of execution, we have a race condition. Example: counter = 5; the producer executes counter++ and the consumer executes counter-- at the same time. Each is three machine steps (load into a register, add or subtract, store). If they interleave as: producer loads 5, consumer loads 5, producer stores 6, consumer stores 4, the result is 4 instead of 5.

## The critical-section problem
Each process has a critical section, the code that accesses shared data. The structure is: entry section, critical section, exit section, remainder section. A solution must satisfy three requirements:
1. Mutual exclusion: if one process is in its critical section, no other process can be in its critical section.
2. Progress: if no process is in its critical section and some want to enter, only those not in their remainder section take part in deciding who enters next, and the decision cannot be postponed forever.
3. Bounded waiting: there is a limit on how many times other processes can enter their critical sections after a process has asked to enter and before it is allowed in.

## Peterson's solution (two processes, Pi and Pj)
Shared variables: boolean flag[2] (flag[i] = true means Pi wants to enter) and int turn (whose turn it is).

    do {
        flag[i] = true;
        turn = j;
        while (flag[j] && turn == j);   // busy wait
        // critical section
        flag[i] = false;
        // remainder section
    } while (true);

It satisfies all three requirements: Pi enters only if flag[j] is false or turn == i, and turn can only be one value, so both cannot be inside together (mutual exclusion); a process that is not interested sets flag to false, so it does not block the other (progress); and after Pj leaves and wants to re-enter, it sets turn = i, so Pi enters after at most one entry by Pj (bounded waiting). Peterson's solution can fail on modern processors that reorder memory operations, unless memory barriers are used.

## Hardware support
- Disabling interrupts works on a single CPU but not on multiprocessors and is dangerous for user programs.
- test_and_set(&lock): atomically returns the old value of lock and sets it to true. Lock: while (test_and_set(&lock)); unlock: lock = false.
- compare_and_swap(&value, expected, new): atomically sets value to new only if it equals expected, and returns the old value.

## Mutex locks
A mutex lock protects a critical section: acquire() before entering, release() after leaving. A mutex implemented with busy waiting is a spinlock. Spinlocks waste CPU time while waiting, but they avoid a context switch, so they are good on multiprocessors when locks are held for a short time.

## Semaphores
A semaphore S is an integer accessed only through two atomic operations:
- wait(S) (also P): while (S <= 0) wait; S--;
- signal(S) (also V): S++;
A counting semaphore can have any value (for example the number of free buffer slots). A binary semaphore is 0 or 1 and works like a mutex.

Uses:
- Mutual exclusion: semaphore mutex = 1; wait(mutex); critical section; signal(mutex).
- Ordering: to make statement S1 in P1 run before S2 in P2, use synch = 0; P1: S1; signal(synch); P2: wait(synch); S2.

Implementation without busy waiting: each semaphore has a value and a list of waiting processes. wait() decrements the value and, if it becomes negative, adds the process to the list and blocks it; signal() increments the value and, if it is still ≤ 0, removes a process from the list and wakes it. With this implementation, a negative value −k means k processes are waiting.

Problems: deadlock (P0: wait(S); wait(Q) while P1: wait(Q); wait(S) can wait for each other forever), starvation (a process is never removed from the waiting list, for example with LIFO order), and priority inversion (a low-priority process holds a lock needed by a high-priority one while a medium-priority process runs; solved with priority inheritance).

## Monitors
A monitor is a language construct: a set of procedures and shared data where only one process can be active inside at a time, so mutual exclusion is automatic. Condition variables (x.wait() and x.signal()) let a process wait inside the monitor until a condition becomes true; x.signal() wakes at most one waiting process and does nothing if none is waiting (unlike a semaphore signal, which is remembered).

## Classical problems
### Bounded-buffer (producer-consumer) with semaphores
Semaphores: mutex = 1, empty = n (free slots), full = 0 (filled slots).

    Producer:                    Consumer:
    wait(empty);                 wait(full);
    wait(mutex);                 wait(mutex);
    add item to buffer           remove item from buffer
    signal(mutex);               signal(mutex);
    signal(full);                signal(empty);

The order matters: if the producer does wait(mutex) before wait(empty) when the buffer is full, it holds the mutex while waiting, the consumer can never enter, and the system deadlocks.

### Readers-writers problem (first variation: readers have priority)
Shared: semaphore rw_mutex = 1, semaphore mutex = 1, int read_count = 0.
- Writer: wait(rw_mutex); write; signal(rw_mutex).
- Reader: wait(mutex); read_count++; if (read_count == 1) wait(rw_mutex); signal(mutex); read; wait(mutex); read_count--; if (read_count == 0) signal(rw_mutex); signal(mutex).
Many readers can read together; a writer needs exclusive access. Writers may starve if readers keep arriving.

### Dining-philosophers problem
Five philosophers sit at a round table with one chopstick between each pair; each needs both neighbouring chopsticks to eat. If each philosopher does wait(chopstick[i]); wait(chopstick[(i + 1) % 5]), all can pick up their left chopstick at once and deadlock. Remedies: allow at most four philosophers at the table, let a philosopher pick up chopsticks only if both are free (inside a critical section or a monitor), or use an asymmetric order (odd philosophers pick up left first, even ones right first).

## Common mistakes
- Forgetting that wait and signal must be atomic.
- Swapping wait(mutex) and wait(empty) in the producer, which can deadlock.
- Thinking a monitor's signal is remembered like a semaphore's. It is lost if nobody is waiting.

## Viva questions
- Name the three requirements of a critical-section solution. Mutual exclusion, progress, bounded waiting.
- Difference between a binary semaphore and a counting semaphore? A binary semaphore is 0 or 1; a counting semaphore counts available resources.
- Why are spinlocks used on multiprocessors? A short busy wait is cheaper than two context switches.
- How does priority inheritance fix priority inversion? The low-priority process holding the lock temporarily gets the high priority, so the medium-priority process cannot preempt it.

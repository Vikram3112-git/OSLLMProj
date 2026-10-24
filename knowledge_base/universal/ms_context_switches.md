# Context Switches (Microsoft Learn, Windows)

Source URL: https://learn.microsoft.com/en-us/windows/win32/procthread/context-switches
Source: Context Switches (Microsoft Learn, Windows)
Licence: CC BY 4.0
Retrieved: 2026-10-12

# Context Switches

The scheduler maintains separate queues of executable threads for each priority level. These threads are known as *ready threads*. When a processor becomes available, the system performs a *context switch*. The steps in a context switch are:

1.  Save the context of the thread that was preempted or voluntarily yielded by the processor.
2.  If the thread remains in a ready state, place it at the end of the queue for its priority level.
3.  Find the highest priority queue that contains ready threads.
4.  Remove the thread at the head of the queue, restore its context, and resume execution.

The following classes of threads are not ready threads.
- Threads created with the CREATE_SUSPENDED flag
- Threads halted during execution with the **SuspendThread** or **SwitchToThread** function
- Threads waiting for a synchronization object or input.

Until threads that are suspended or blocked become ready to run, the scheduler does not allocate any processor time to them, regardless of their priority.

The most common reasons for a context switch are:
- The time slice has elapsed.
- A thread with a higher priority has become ready to run.
- A running thread needs to wait.

When a running thread needs to wait, it relinquishes the remainder of its time slice.
# Priority Boosts (Microsoft Learn, Windows)

Source URL: https://learn.microsoft.com/en-us/windows/win32/procthread/priority-boosts
Source: Priority Boosts (Microsoft Learn, Windows)
Licence: CC BY 4.0
Retrieved: 2026-10-12

# Priority Boosts

Each thread has a *dynamic priority*. This is the priority the scheduler uses to determine which thread to execute. Initially, a thread's dynamic priority is the same as its base priority. The system can boost and lower the dynamic priority, to ensure that it is responsive and that no threads are starved for processor time. The system does not boost the priority of threads with a base priority level between 16 and 31. Only threads with a base priority between 0 and 15 receive dynamic priority boosts.

The system boosts the dynamic priority of a thread to enhance its responsiveness as follows.
- When a process that uses NORMAL_PRIORITY_CLASS is brought to the foreground, the scheduler boosts the priority class of the process associated with the foreground window, so that it is greater than or equal to the priority class of any background processes. The priority class returns to its original setting when the process is no longer in the foreground.
- When a window receives input, such as timer messages, mouse messages, or keyboard input, the scheduler boosts the priority of the thread that owns the window.
- When the wait conditions for a blocked thread are satisfied, the scheduler boosts the priority of the thread. For example, when a wait operation associated with disk or keyboard I/O finishes, the thread receives a priority boost.

    You can disable the priority-boosting feature by calling the **SetProcessPriorityBoost** or **SetThreadPriorityBoost** function. To determine whether this feature has been disabled, call the **GetProcessPriorityBoost** or **GetThreadPriorityBoost** function.

After raising a thread's dynamic priority, the scheduler reduces that priority by one level each time the thread completes a time slice, until the thread drops back to its base priority. A thread's dynamic priority is never less than its base priority.
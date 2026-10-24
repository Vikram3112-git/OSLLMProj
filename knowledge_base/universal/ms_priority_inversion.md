# Priority Inversion (Microsoft Learn, Windows)

Source URL: https://learn.microsoft.com/en-us/windows/win32/procthread/priority-inversion
Source: Priority Inversion (Microsoft Learn, Windows)
Licence: CC BY 4.0
Retrieved: 2026-10-12

# Priority Inversion

A phenomenon known as **priority inversion** occurs when a high–priority thread is indefinitely delayed while awaiting a resource held by a low–priority thread that cannot proceed due to the presence of an unrelated medium–priority thread. As a result, the high–priority thread is effectively denied access to the CPU by the lower medium–priority thread.

For example, a thread T1 running at priority 4 gets preempted by a higher-priority thread T2 with a priority of 8 after acquiring a lock. Subsequently, a thread T3 with a priority of 12 arrives, preempts T2, and gets blocked trying to acquire the lock held by T1. At this point, both T1 and T2 are ready to run, but since T2 has a higher priority, it continues to execute, effectively preventing T3, a higher–priority thread, from making progress because T1 is unable to run and release the lock.

The thread scheduler addresses this issue through a feature called AutoBoost. AutoBoost automatically tracks resource reservations and adjusts thread priorities by applying priority floors that a thread must never fall below. For example, if a low–priority thread acquires a critical section and a higher–priority thread is blocked waiting for the critical section, the priority of the owner is raised to the maximum priority of the waiter until it releases the resource.
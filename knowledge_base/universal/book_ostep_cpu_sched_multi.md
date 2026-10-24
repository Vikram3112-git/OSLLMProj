# Multiprocessor Scheduling (Advanced) (Operating Systems: Three Easy Pieces)

Source URL: https://pages.cs.wisc.edu/~remzi/OSTEP/cpu-sched-multi.pdf
Source: Multiprocessor Scheduling (Advanced) (Operating Systems: Three Easy Pieces)
Licence: Free online textbook by the authors; downloaded for personal study, not redistributed
Retrieved: 2026-10-12

Multiprocessor Scheduling (Advanced)

This chapter will introduce the basics of multiprocessor scheduling. As this topic is relatively advanced, it may be best to cover it after you have studied the topic of concurrency in some detail (i.e., the second major “easy piece” of the book).

After years of existence only in the high-end of the computing spectrum, multiprocessor systems are increasingly commonplace, and have found their way into desktop machines, laptops, and even mobile devices. The rise of the multicore processor, in which multiple CPU cores are packed onto a single chip, is the source of this proliferation; these chips have become popular as computer architects have had a difﬁcult time making a single CPU much faster without using (way) too much power. And thus we all now have a few CPUs available to us, which is a good thing, right?

Of course, there are many difﬁculties that arise with the arrival of more than a single CPU. A primary one is that a typical application (i.e., some C program you wrote) only uses a single CPU; adding more CPUs does not make that single application run faster. To remedy this problem, you’ll have to rewrite your application to run in parallel, perhaps using threads (as discussed in great detail in the second piece of this book). Multithreaded applications can spread work across multiple CPUs and thus run faster when given more CPU resources.

ASIDE: ADVANCED CHAPTERS Advanced chapters require material from a broad swath of the book to truly understand, while logically ﬁtting into a section that is earlier than said set of prerequisite materials. For example, this chapter on multiprocessor scheduling makes much more sense if you’ve ﬁrst read the middle piece on concurrency; however, it logically ﬁts into the part of the book on virtualization (generally) and CPU scheduling (speciﬁcally). Thus, it is recommended such chapters be covered out of order; in this case, after the second piece of the book.

Memory

CPU

Cache

Figure 10.1: Single CPU With Cache

Beyond applications, a new problem that arises for the operating system is (not surprisingly!) that of multiprocessor scheduling. Thus far we’ve discussed a number of principles behind single-processor scheduling; how can we extend those ideas to work on multiple CPUs? What new problems must we overcome? And thus, our problem:

CRUX: HOW TO SCHEDULE JOBS ON MULTIPLE CPUS How should the OS schedule jobs on multiple CPUs? What new problems arise? Do the same old techniques work, or are new ideas required?

10.1 Background: Multiprocessor Architecture

To understand the new issues surrounding multiprocessor scheduling, we have to understand a new and fundamental difference between single-CPU hardware and multi-CPU hardware. This difference centers around the use of hardware caches (e.g., Figure 10.1), and exactly how data is shared across multiple processors. We now discuss this issue further, at a high level. Details are available elsewhere [CSG99], in particular in an upper-level or perhaps graduate computer architecture course.

In a system with a single CPU, there are a hierarchy of hardware caches that in general help the processor run programs faster. Caches are small, fast memories that (in general) hold copies of popular data that is found in the main memory of the system. Main memory, in contrast, holds all of the data, but access to this larger memory is slower. By keeping frequently accessed data in a cache, the system can make the large, slow memory appear to be a fast one.

Memory

CPU CPU

Cache Cache

Bus

Figure 10.2: Two CPUs With Caches Sharing Memory

As an example, consider a program that issues an explicit load instruction to fetch a value from memory, and a simple system with only a single CPU; the CPU has a small cache (say 64 KB) and a large main memory. The ﬁrst time a program issues this load, the data resides in main memory, and thus takes a long time to fetch (perhaps in the tens of nanoseconds, or even hundreds). The processor, anticipating that the data may be reused, puts a copy of the loaded data into the CPU cache. If the program later fetches this same data item again, the CPU ﬁrst checks for it in the cache; if it ﬁnds it there, the data is fetched much more quickly (say, just a few nanoseconds), and thus the program runs faster.

Caches are thus based on the notion of locality, of which there are two kinds: temporal locality and spatial locality. The idea behind temporal locality is that when a piece of data is accessed, it is likely to be accessed again in the near future; imagine variables or even instructions themselves being accessed over and over again in a loop. The idea behind spatial locality is that if a program accesses a data item at address x, it is likely to access data items near x as well; here, think of a program streaming through an array, or instructions being executed one after the other. Because locality of these types exist in many programs, hardware systems can make good guesses about which data to put in a cache and thus work well.

Now for the tricky part: what happens when you have multiple processors in a single system, with a single shared main memory, as we see in Figure 10.2?

As it turns out, caching with multiple CPUs is much more complicated. Imagine, for example, that a program running on CPU 1 reads a data item (with value D) at address A; because the data is not in the cache on CPU 1, the system fetches it from main memory, and gets the

EASY PIECES

value D. The program then modiﬁes the value at address A, just updating its cache with the new value D′; writing the data through all the way to main memory is slow, so the system will (usually) do that later. Then assume the OS decides to stop running the program and move it to CPU 2. The program then re-reads the value at address A; there is no such data in CPU 2’s cache, and thus the system fetches the value from main memory, and gets the old value D instead of the correct value D′. Oops!

This general problem is called the problem of cache coherence, and there is a vast research literature that describes many different subtleties involved with solving the problem [SHW11]. Here, we will skip all of the nuance and make some major points; take a computer architecture class (or three) to learn more.

The basic solution is provided by the hardware: by monitoring memory accesses, hardware can ensure that basically the “right thing” happens and that the view of a single shared memory is preserved. One way to do this on a bus-based system (as described above) is to use an old technique known as bus snooping [G83]; each cache pays attention to memory updates by observing the bus that connects them to main memory. When a CPU then sees an update for a data item it holds in its cache, it will notice the change and either invalidate its copy (i.e., remove it from its own cache) or update it (i.e., put the new value into its cache too). Write-back caches, as hinted at above, make this more complicated (because the write to main memory isn’t visible until later), but you can imagine how the basic scheme might work.

10.2 Don’t Forget Synchronization

Given that the caches do all of this work to provide coherence, do programs (or the OS itself) have to worry about anything when they access shared data? The answer, unfortunately, is yes, and is documented in great detail in the second piece of this book on the topic of concurrency. While we won’t get into the details here, we’ll sketch/review some of the basic ideas here (assuming you’re familiar with concurrency).

When accessing (and in particular, updating) shared data items or structures across CPUs, mutual exclusion primitives (such as locks) should likely be used to guarantee correctness (other approaches, such as building lock-free data structures, are complex and only used on occasion; see the chapter on deadlock in the piece on concurrency for details). For example, assume we have a shared queue being accessed on multiple CPUs concurrently. Without locks, adding or removing elements from the queue concurrently will not work as expected, even with the underlying coherence protocols; one needs locks to atomically update the data structure to its new state.

To make this more concrete, imagine this code sequence, which is used to remove an element from a shared linked list, as we see in Figure 10.3. Imagine if threads on two CPUs enter this routine at the same time. If

1 typedef struct __Node_t {

2 int value;

3 struct __Node_t *next;

4 } Node_t;

6 int List_Pop() {

7 Node_t *tmp = head; // remember old head

8 int value = head->value; // ... and its value

9 head = head->next; // advance to next

10 free(tmp); // free old head

11 return value; // return value @head

12 }

Figure 10.3: Simple List Delete Code

Thread 1 executes the ﬁrst line, it will have the current value of head stored in its tmp variable; if Thread 2 then executes the ﬁrst line as well, it also will have the same value of head stored in its own private tmp variable (tmp is allocated on the stack, and thus each thread will have its own private storage for it). Thus, instead of each thread removing an element from the head of the list, each thread will try to remove the same head element, leading to all sorts of problems (such as an attempted double free of the head element at Line 10, as well as potentially returning the same data value twice).

The solution, of course, is to make such routines correct via locking. In this case, allocating a simple mutex (e.g., pthread_mutex_t m;) and then adding a lock(&m) at the beginning of the routine and an unlock(&m) at the end will solve the problem, ensuring that the code will execute as desired. Unfortunately, as we will see, such an approach is not without problems, in particular with regards to performance. Speciﬁcally, as the number of CPUs grows, access to a synchronized shared data structure becomes quite slow.

10.3 One Final Issue: Cache Afﬁnity

One ﬁnal issue arises in building a multiprocessor cache scheduler, known as cache afﬁnity [TTG95]. This notion is simple: a process, when run on a particular CPU, builds up a fair bit of state in the caches (and TLBs) of the CPU. The next time the process runs, it is often advantageous to run it on the same CPU, as it will run faster if some of its state is already present in the caches on that CPU. If, instead, one runs a process on a different CPU each time, the performance of the process will be worse, as it will have to reload the state each time it runs (note it will run correctly on a different CPU thanks to the cache coherence protocols of the hardware). Thus, a multiprocessor scheduler should consider cache afﬁnity when making its scheduling decisions, perhaps preferring to keep a process on the same CPU if at all possible.

EASY PIECES

10.4 Single-Queue Scheduling

With this background in place, we now discuss how to build a scheduler for a multiprocessor system. The most basic approach is to simply reuse the basic framework for single processor scheduling, by putting all jobs that need to be scheduled into a single queue; we call this singlequeue multiprocessor scheduling or SQMS for short. This approach has the advantage of simplicity; it does not require much work to take an existing policy that picks the best job to run next and adapt it to work on more than one CPU (where it might pick the best two jobs to run, if there are two CPUs, for example).

However, SQMS has obvious shortcomings. The ﬁrst problem is a lack of scalability. To ensure the scheduler works correctly on multiple CPUs, the developers will have inserted some form of locking into the code, as described above. Locks ensure that when SQMS code accesses the single queue (say, to ﬁnd the next job to run), the proper outcome arises.

Locks, unfortunately, can greatly reduce performance, particularly as the number of CPUs in the systems grows [A90]. As contention for such a single lock increases, the system spends more and more time in lock overhead and less time doing the work the system should be doing (note: it would be great to include a real measurement of this in here someday).

The second main problem with SQMS is cache afﬁnity. For example, let us assume we have ﬁve jobs to run (A, B, C, D, E) and four processors. Our scheduling queue thus looks like this:

Queue A B C D E NULL

Over time, assuming each job runs for a time slice and then another job is chosen, here is a possible job schedule across CPUs:

D C B A E

C B A E D

B A E D C

A E D C B

... (repeat) ...

... (repeat) ...

... (repeat) ...

... (repeat) ...

Because each CPU simply picks the next job to run from the globallyshared queue, each job ends up bouncing around from CPU to CPU, thus doing exactly the opposite of what would make sense from the standpoint of cache afﬁnity.

To handle this problem, most SQMS schedulers include some kind of afﬁnity mechanism to try to make it more likely that process will continue

to run on the same CPU if possible. Speciﬁcally, one might provide afﬁnity for some jobs, but move others around to balance load. For example, imagine the same ﬁve jobs scheduled as follows:

D D D D E

C C C E C

B B E B B

A E A A A

... (repeat) ...

... (repeat) ...

... (repeat) ...

... (repeat) ...

In this arrangement, jobs A through D are not moved across processors, with only job E migrating from CPU to CPU, thus preserving afﬁnity for most. You could then decide to migrate a different job the next time through, thus achieving some kind of afﬁnity fairness as well. Implementing such a scheme, however, can be complex.

Thus, we can see the SQMS approach has its strengths and weaknesses. It is straightforward to implement given an existing single-CPU scheduler, which by deﬁnition has only a single queue. However, it does not scale well (due to synchronization overheads), and it does not readily preserve cache afﬁnity.

10.5 Multi-Queue Scheduling

Because of the problems caused in single-queue schedulers, some systems opt for multiple queues, e.g., one per CPU. We call this approach multi-queue multiprocessor scheduling (or MQMS).

In MQMS, our basic scheduling framework consists of multiple scheduling queues. Each queue will likely follow a particular scheduling discipline, such as round robin, though of course any algorithm can be used. When a job enters the system, it is placed on exactly one scheduling queue, according to some heuristic (e.g., random, or picking one with fewer jobs than others). Then it is scheduled essentially independently, thus avoiding the problems of information sharing and synchronization found in the single-queue approach.

For example, assume we have a system where there are just two CPUs (labeled CPU 0 and CPU 1), and some number of jobs enter the system: A, B, C, and D for example. Given that each CPU has a scheduling queue now, the OS has to decide into which queue to place each job. It might do something like this:

Q0 A C Q1 B D

EASY PIECES

Depending on the queue scheduling policy, each CPU now has two jobs to choose from when deciding what should run. For example, with round robin, the system might produce a schedule that looks like this:

CPU 0 A A C C A A C C A A C C

B B D D B B D D B B D D ...

...

MQMS has a distinct advantage over SQMS in that it should be inherently more scalable. As the number of CPUs grows, so too does the number of queues, and thus lock and cache contention should not become a central problem. In addition, MQMS intrinsically provides cache afﬁnity; jobs stay on the same CPU and thus reap the advantage of reusing cached contents therein.

But, if you’ve been paying attention, you might see that we have a new problem, which is fundamental in the multi-queue based approach: load imbalance. Let’s assume we have the same set up as above (four jobs, two CPUs), but then one of the jobs (say C) ﬁnishes. We now have the following scheduling queues:

Q0 A Q1 B D

If we then run our round-robin policy on each queue of the system, we will see this resulting schedule:

CPU 0 A A A A A A A A A A A A

B B D D B B D D B B D D ...

...

As you can see from this diagram, A gets twice as much CPU as B and D, which is not the desired outcome. Even worse, let’s imagine that both A and C ﬁnish, leaving just jobs B and D in the system. The two scheduling queues, and resulting timeline, will look like this:

Q0 Q1 B D

CPU 1 B B D D B B D D B B D D ...

How terrible – CPU 0 is idle! (insert dramatic and sinister music here) And thus our CPU usage timeline looks quite sad.

So what should a poor multi-queue multiprocessor scheduler do? How can we overcome the insidious problem of load imbalance and defeat the evil forces of ... the Decepticons1? How do we stop asking questions that are hardly relevant to this otherwise wonderful book?

CRUX: HOW TO DEAL WITH LOAD IMBALANCE How should a multi-queue multiprocessor scheduler handle load imbalance, so as to better achieve its desired scheduling goals?

The obvious answer to this query is to move jobs around, a technique which we (once again) refer to as migration. By migrating a job from one CPU to another, true load balance can be achieved.

Let’s look at a couple of examples to add some clarity. Once again, we have a situation where one CPU is idle and the other has some jobs.

Q0 Q1 B D

In this case, the desired migration is easy to understand: the OS should simply move one of B or D to CPU 0. The result of this single job migration is evenly balanced load and everyone is happy.

A more tricky case arises in our earlier example, where A was left alone on CPU 0 and B and D were alternating on CPU 1:

Q0 A Q1 B D

In this case, a single migration does not solve the problem. What would you do in this case? The answer, alas, is continuous migration of one or more jobs. One possible solution is to keep switching jobs, as we see in the following timeline. In the ﬁgure, ﬁrst A is alone on CPU 0, and B and D alternate on CPU 1. After a few time slices, B is moved to compete with A on CPU 0, while D enjoys a few time slices alone on CPU 1. And thus load is balanced:

A A A A B A B A B B B B

B D B D D D D D A D A D ...

...

Of course, many other possible migration patterns exist. But now for the tricky part: how should the system decide to enact such a migration?

1Little known fact is that the home planet of Cybertron was destroyed by bad CPU scheduling decisions. And now let that be the ﬁrst and last reference to Transformers in this book, for which we sincerely apologize.

EASY PIECES

One basic approach is to use a technique known as work stealing [FLR98]. With a work-stealing approach, a (source) queue that is low on jobs will occasionally peek at another (target) queue, to see how full it is. If the target queue is (notably) more full than the source queue, the source will “steal” one or more jobs from the target to help balance load.

Of course, there is a natural tension in such an approach. If you look around at other queues too often, you will suffer from high overhead and have trouble scaling, which was the entire purpose of implementing the multiple queue scheduling in the ﬁrst place! If, on the other hand, you don’t look at other queues very often, you are in danger of suffering from severe load imbalances. Finding the right threshold remains, as is common in system policy design, a black art.

10.6 Linux Multiprocessor Schedulers Interestingly, in the Linux community, no common solution has emerged to building a multiprocessor scheduler. Over time, three different schedulers arose: the O(1) scheduler, the Completely Fair Scheduler (CFS), and the BF Scheduler (BFS)2. See Meehean’s dissertation for an excellent overview of the strengths and weaknesses of said schedulers [M11]; here we just summarize a few of the basics.

Both O(1) and CFS use multiple queues, whereas BFS uses a single queue, showing that both approaches can be successful. Of course, there are many other details which separate these schedulers. For example, the O(1) scheduler is a priority-based scheduler (similar to the MLFQ discussed before), changing a process’s priority over time and then scheduling those with highest priority in order to meet various scheduling objectives; interactivity is a particular focus. CFS, in contrast, is a deterministic proportional-share approach (more like Stride scheduling, as discussed earlier). BFS, the only single-queue approach among the three, is also proportional-share, but based on a more complicated scheme known as Earliest Eligible Virtual Deadline First (EEVDF) [SA96]. Read more about these modern algorithms on your own; you should be able to understand how they work now!

10.7 Summary We have seen various approaches to multiprocessor scheduling. The single-queue approach (SQMS) is rather straightforward to build and balances load well but inherently has difﬁculty with scaling to many processors and cache afﬁnity. The multiple-queue approach (MQMS) scales better and handles cache afﬁnity well, but has trouble with load imbalance and is more complicated. Whichever approach you take, there is no simple answer: building a general purpose scheduler remains a daunting task, as small code changes can lead to large behavioral differences. Only undertake such an exercise if you know exactly what you are doing, or, at least, are getting paid a large amount of money to do so.

2Look up what BF stands for on your own; be forewarned, it is not for the faint of heart.
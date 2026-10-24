# Beyond Physical Memory: Policies (Operating Systems: Three Easy Pieces)

Source URL: https://pages.cs.wisc.edu/~remzi/OSTEP/vm-beyondphys-policy.pdf
Source: Beyond Physical Memory: Policies (Operating Systems: Three Easy Pieces)
Licence: Free online textbook by the authors; downloaded for personal study, not redistributed
Retrieved: 2026-10-23

Beyond Physical Memory: Policies

In a virtual memory manager, life is easy when you have a lot of free memory. A page fault occurs, you ﬁnd a free page on the free-page list, and assign it to the faulting page. Hey, Operating System, congratulations! You did it again.

Unfortunately, things get a little more interesting when little memory is free. In such a case, this memory pressure forces the OS to start paging out pages to make room for actively-used pages. Deciding which page (or pages) to evict is encapsulated within the replacement policy of the OS; historically, it was one of the most important decisions the early virtual memory systems made, as older systems had little physical memory. Minimally, it is an interesting set of policies worth knowing a little more about. And thus our problem:

THE CRUX: HOW TO DECIDE WHICH PAGE TO EVICT How can the OS decide which page (or pages) to evict from memory? This decision is made by the replacement policy of the system, which usually follows some general principles (discussed below) but also includes certain tweaks to avoid corner-case behaviors.

22.1 Cache Management Before diving into policies, we ﬁrst describe the problem we are trying to solve in more detail. Given that main memory holds some subset of all the pages in the system, it can rightly be viewed as a cache for virtual memory pages in the system. Thus, our goal in picking a replacement policy for this cache is to minimize the number of cache misses, i.e., to minimize the number of times that we have to fetch a page from disk. Alternately, one can view our goal as maximizing the number of cache hits, i.e., the number of times a page that is accessed is found in memory.

Knowing the number of cache hits and misses let us calculate the average memory access time (AMAT) for a program (a metric computer architects compute for hardware caches [HP06]). Speciﬁcally, given these values, we can compute the AMAT of a program as follows:

AMAT = TM + (PMiss · TD) (22.1)

where TM represents the cost of accessing memory, TD the cost of accessing disk, and PMiss the probability of not ﬁnding the data in the cache (a miss); PMiss varies from 0.0 to 1.0, and sometimes we refer to a percent miss rate instead of a probability (e.g., a 10% miss rate means PMiss = 0.10). Note you always pay the cost of accessing the data in memory; when you miss, however, you must additionally pay the cost of fetching the data from disk.

For example, let us imagine a machine with a (tiny) address space: 4KB, with 256-byte pages. Thus, a virtual address has two components: a 4-bit VPN (the most-signiﬁcant bits) and an 8-bit offset (the least-signiﬁcant bits). Thus, a process in this example can access 24 or 16 total virtual pages. In this example, the process generates the following memory references (i.e., virtual addresses): 0x000, 0x100, 0x200, 0x300, 0x400, 0x500, 0x600, 0x700, 0x800, 0x900. These virtual addresses refer to the ﬁrst byte of each of the ﬁrst ten pages of the address space (the page number being the ﬁrst hex digit of each virtual address).

Let us further assume that every page except virtual page 3 is already in memory. Thus, our sequence of memory references will encounter the following behavior: hit, hit, hit, miss, hit, hit, hit, hit, hit, hit. We can compute the hit rate (the percent of references found in memory): 90%, as 9 out of 10 references are in memory. The miss rate is thus 10% (PMiss = 0.1). In general, PHit + PMiss = 1.0; hit rate plus miss rate sum to 100%. To calculate AMAT, we need to know the cost of accessing memory and the cost of accessing disk. Assuming the cost of accessing memory (TM) is around 100 nanoseconds, and the cost of accessing disk (TD) is about 10 milliseconds, we have the following AMAT: 100ns + 0.1 · 10ms, which is 100ns + 1ms, or 1.0001 ms, or about 1 millisecond. If our hit rate had instead been 99.9% (Pmiss = 0.001), the result is quite different: AMAT is 10.1 microseconds, or roughly 100 times faster. As the hit rate approaches 100%, AMAT approaches 100 nanoseconds.

Unfortunately, as you can see in this example, the cost of disk access is so high in modern systems that even a tiny miss rate will quickly dominate the overall AMAT of running programs. Clearly, we need to avoid as many misses as possible or run slowly, at the rate of the disk. One way to help with this is to carefully develop a smart policy, as we now do.

22.2 The Optimal Replacement Policy

To better understand how a particular replacement policy works, it would be nice to compare it to the best possible replacement policy. As it turns out, such an optimal policy was developed by Belady many years ago [B66] (he originally called it MIN). The optimal replacement policy leads to the fewest number of misses overall. Belady showed that a simple (but, unfortunately, difﬁcult to implement!) approach that replaces the page that will be accessed furthest in the future is the optimal policy, resulting in the fewest-possible cache misses.

TIP: COMPARING AGAINST OPTIMAL IS USEFUL Although optimal is not very practical as a real policy, it is incredibly useful as a comparison point in simulation or other studies. Saying that your fancy new algorithm has a 80% hit rate isn’t meaningful in isolation; saying that optimal achieves an 82% hit rate (and thus your new approach is quite close to optimal) makes the result more meaningful and gives it context. Thus, in any study you perform, knowing what the optimal is lets you perform a better comparison, showing how much improvement is still possible, and also when you can stop making your policy better, because it is close enough to the ideal [AD03].

Hopefully, the intuition behind the optimal policy makes sense. Think about it like this: if you have to throw out some page, why not throw out the one that is needed the furthest from now? By doing so, you are essentially saying that all the other pages in the cache are more important than the one furthest out. The reason this is true is simple: you will refer to the other pages before you refer to the one furthest out.

Let’s trace through a simple example to understand the decisions the optimal policy makes. Assume a program accesses the following stream of virtual pages: 0, 1, 2, 0, 1, 3, 0, 3, 1, 2, 1. Figure 22.1 shows the behavior of optimal, assuming a cache that ﬁts three pages.

In the ﬁgure, you can see the following actions. Not surprisingly, the ﬁrst three accesses are misses, as the cache begins in an empty state; such a miss is sometimes referred to as a cold-start miss (or compulsory miss). Then we refer again to pages 0 and 1, which both hit in the cache. Finally, we reach another miss (to page 3), but this time the cache is full; a replacement must take place! Which begs the question: which page should we replace? With the optimal policy, we examine the future for each page currently in the cache (0, 1, and 2), and see that 0 is accessed almost immediately, 1 is accessed a little later, and 2 is accessed furthest in the future. Thus the optimal policy has an easy choice: evict page 2, resulting in

Resulting Access Hit/Miss? Evict Cache State 0 Miss 0 1 Miss 0, 1 2 Miss 0, 1, 2 0 Hit 0, 1, 2 1 Hit 0, 1, 2 3 Miss 2 0, 1, 3 0 Hit 0, 1, 3 3 Hit 0, 1, 3 1 Hit 0, 1, 3 2 Miss 3 0, 1, 2 1 Hit 0, 1, 2

Figure 22.1: Tracing The Optimal Policy

EASY PIECES

ASIDE: TYPES OF CACHE MISSES In the computer architecture world, architects sometimes ﬁnd it useful to characterize misses by type, into one of three categories: compulsory, capacity, and conﬂict misses, sometimes called the Three C’s [H87]. A compulsory miss (or cold-start miss [EF78]) occurs because the cache is empty to begin with and this is the ﬁrst reference to the item; in contrast, a capacity miss occurs because the cache ran out of space and had to evict an item to bring a new item into the cache. The third type of miss (a conﬂict miss) arises in hardware because of limits on where an item can be placed in a hardware cache, due to something known as setassociativity; it does not arise in the OS page cache because such caches are always fully-associative, i.e., there are no restrictions on where in memory a page can be placed. See H&P for details [HP06].

pages 0, 1, and 3 in the cache. The next three references are hits, but then we get to page 2, which we evicted long ago, and suffer another miss. Here the optimal policy again examines the future for each page in the cache (0, 1, and 3), and sees that as long as it doesn’t evict page 1 (which is about to be accessed), we’ll be OK. The example shows page 3 getting evicted, although 0 would have been a ﬁne choice too. Finally, we hit on page 1 and the trace completes.

We can also calculate the hit rate for the cache: with 6 hits and 5 misses, the hit rate is Hits Hits+Misses which is 6 6+5 or 54.5%. You can also compute the hit rate modulo compulsory misses (i.e., ignore the ﬁrst miss to a given page), resulting in a 85.7% hit rate.

Unfortunately, as we saw before in the development of scheduling policies, the future is not generally known; you can’t build the optimal policy for a general-purpose operating system1. Thus, in developing a real, deployable policy, we will focus on approaches that ﬁnd some other way to decide which page to evict. The optimal policy will thus serve only as a comparison point, to know how close we are to “perfect”.

22.3 A Simple Policy: FIFO

Many early systems avoided the complexity of trying to approach optimal and employed very simple replacement policies. For example, some systems used FIFO (ﬁrst-in, ﬁrst-out) replacement, where pages were simply placed in a queue when they enter the system; when a replacement occurs, the page on the tail of the queue (the “ﬁrst-in” page) is evicted. FIFO has one great strength: it is quite simple to implement.

Let’s examine how FIFO does on our example reference stream (Figure 22.2, page 5). We again begin our trace with three compulsory misses to

1If you can, let us know! We can become rich together. Or, like the scientists who “discovered” cold fusion, widely scorned and mocked [FP89].

Resulting Access Hit/Miss? Evict Cache State 0 Miss First-in→ 0 1 Miss First-in→ 0, 1 2 Miss First-in→ 0, 1, 2 0 Hit First-in→ 0, 1, 2 1 Hit First-in→ 0, 1, 2 3 Miss 0 First-in→ 1, 2, 3 0 Miss 1 First-in→ 2, 3, 0 3 Hit First-in→ 2, 3, 0 1 Miss 2 First-in→ 3, 0, 1 2 Miss 3 First-in→ 0, 1, 2 1 Hit First-in→ 0, 1, 2

Figure 22.2: Tracing The FIFO Policy pages 0, 1, and 2, and then hit on both 0 and 1. Next, page 3 is referenced, causing a miss; the replacement decision is easy with FIFO: pick the page that was the “ﬁrst one” in (the cache state in the ﬁgure is kept in FIFO order, with the ﬁrst-in page on the left), which is page 0. Unfortunately, our next access is to page 0, causing another miss and replacement (of page 1). We then hit on page 3, but miss on 1 and 2, and ﬁnally hit on 1.

Comparing FIFO to optimal, FIFO does notably worse: a 36.4% hit rate (or 57.1% excluding compulsory misses). FIFO simply can’t determine the importance of blocks: even though page 0 had been accessed a number of times, FIFO still kicks it out, simply because it was the ﬁrst one brought into memory.

ASIDE: BELADY’S ANOMALY Belady (of the optimal policy) and colleagues found an interesting reference stream that behaved a little unexpectedly [BNS69]. The memoryreference stream: 1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5. The replacement policy they were studying was FIFO. The interesting part: how the cache hit rate changed when moving from a cache size of 3 to 4 pages.

In general, you would expect the cache hit rate to increase (get better) when the cache gets larger. But in this case, with FIFO, it gets worse! Calculate the hits and misses yourself and see. This odd behavior is generally referred to as Belady’s Anomaly (to the chagrin of his co-authors).

Some other policies, such as LRU, don’t suffer from this problem. Can you guess why? As it turns out, LRU has what is known as a stack property [M+70]. For algorithms with this property, a cache of size N + 1 naturally includes the contents of a cache of size N. Thus, when increasing the cache size, hit rate will either stay the same or improve. FIFO and Random (among others) clearly do not obey the stack property, and thus are susceptible to anomalous behavior.

EASY PIECES

Resulting Access Hit/Miss? Evict Cache State 0 Miss 0 1 Miss 0, 1 2 Miss 0, 1, 2 0 Hit 0, 1, 2 1 Hit 0, 1, 2 3 Miss 0 1, 2, 3 0 Miss 1 2, 3, 0 3 Hit 2, 3, 0 1 Miss 3 2, 0, 1 2 Hit 2, 0, 1 1 Hit 2, 0, 1

Figure 22.3: Tracing The Random Policy

22.4 Another Simple Policy: Random

Another similar replacement policy is Random, which simply picks a random page to replace under memory pressure. Random has properties similar to FIFO; it is simple to implement, but it doesn’t really try to be too intelligent in picking which blocks to evict. Let’s look at how Random does on our famous example reference stream (see Figure 22.3).

Of course, how Random does depends entirely upon how lucky (or unlucky) Random gets in its choices. In the example above, Random does a little better than FIFO, and a little worse than optimal. In fact, we can run the Random experiment thousands of times and determine how it does in general. Figure 22.4 shows how many hits Random achieves over 10,000 trials, each with a different random seed. As you can see, sometimes (just over 40% of the time), Random is as good as optimal, achieving 6 hits on the example trace; sometimes it does much worse, achieving 2 hits or fewer. How Random does depends on the luck of the draw.

0 1 2 3 4 5 6 7 0

Number of Hits

Frequency

Figure 22.4: Random Performance Over 10,000 Trials

Resulting Access Hit/Miss? Evict Cache State 0 Miss LRU→ 0 1 Miss LRU→ 0, 1 2 Miss LRU→ 0, 1, 2 0 Hit LRU→ 1, 2, 0 1 Hit LRU→ 2, 0, 1 3 Miss 2 LRU→ 0, 1, 3 0 Hit LRU→ 1, 3, 0 3 Hit LRU→ 1, 0, 3 1 Hit LRU→ 0, 3, 1 2 Miss 0 LRU→ 3, 1, 2 1 Hit LRU→ 3, 2, 1

Figure 22.5: Tracing The LRU Policy 22.5 Using History: LRU

Unfortunately, any policy as simple as FIFO or Random is likely to have a common problem: it might kick out an important page, one that is about to be referenced again. FIFO kicks out the page that was ﬁrst brought in; if this happens to be a page with important code or data structures upon it, it gets thrown out anyhow, even though it will soon be paged back in. Thus, FIFO, Random, and similar policies are not likely to approach optimal; something smarter is needed.

As we did with scheduling policy, to improve our guess at the future, we once again lean on the past and use history as our guide. For example, if a program has accessed a page in the near past, it is likely to access it again in the near future.

One type of historical information a page-replacement policy could use is frequency; if a page has been accessed many times, perhaps it should not be replaced as it clearly has some value. A more commonlyused property of a page is its recency of access; the more recently a page has been accessed, perhaps the more likely it will be accessed again.

This family of policies is based on what people refer to as the principle of locality [D70], which basically is just an observation about programs and their behavior. What this principle says, quite simply, is that programs tend to access certain code sequences (e.g., in a loop) and data structures (e.g., an array accessed by the loop) quite frequently; we should thus try to use history to ﬁgure out which pages are important, and keep those pages in memory when it comes to eviction time.

And thus, a family of simple historically-based algorithms are born. The Least-Frequently-Used (LFU) policy replaces the least-frequentlyused page when an eviction must take place. Similarly, the Least-Recently- Used (LRU) policy replaces the least-recently-used page. These algorithms are easy to remember: once you know the name, you know exactly what it does, which is an excellent property for a name.

To better understand LRU, let’s examine how LRU does on our exam-

EASY PIECES

ASIDE: TYPES OF LOCALITY There are two types of locality that programs tend to exhibit. The ﬁrst is known as spatial locality, which states that if a page P is accessed, it is likely the pages around it (say P −1 or P + 1) will also likely be accessed. The second is temporal locality, which states that pages that have been accessed in the near past are likely to be accessed again in the near future. The assumption of the presence of these types of locality plays a large role in the caching hierarchies of hardware systems, which deploy many levels of instruction, data, and address-translation caching to help programs run fast when such locality exists. Of course, the principle of locality, as it is often called, is no hard-andfast rule that all programs must obey. Indeed, some programs access memory (or disk) in rather random fashion and don’t exhibit much or any locality in their access streams. Thus, while locality is a good thing to keep in mind while designing caches of any kind (hardware or software), it does not guarantee success. Rather, it is a heuristic that often proves useful in the design of computer systems.

ple reference stream. Figure 22.5 (page 7) shows the results. From the ﬁgure, you can see how LRU can use history to do better than stateless policies such as Random or FIFO. In the example, LRU evicts page 2 when it ﬁrst has to replace a page, because 0 and 1 have been accessed more recently. It then replaces page 0 because 1 and 3 have been accessed more recently. In both cases, LRU’s decision, based on history, turns out to be correct, and the next references are thus hits. Thus, in our example, LRU does as well as possible, matching optimal in its performance2.

We should also note that the opposites of these algorithms exist: Most- Frequently-Used (MFU) and Most-Recently-Used (MRU). In most cases (not all!), these policies do not work well, as they ignore the locality most programs exhibit instead of embracing it.

22.6 Workload Examples

Let’s look at a few more examples in order to better understand how some of these policies behave. Here, we’ll examine more complex workloads instead of small traces. However, even these workloads are greatly simpliﬁed; a better study would include application traces.

Our ﬁrst workload has no locality, which means that each reference is to a random page within the set of accessed pages. In this simple example, the workload accesses 100 unique pages over time, choosing the next page to refer to at random; overall, 10,000 pages are accessed. In the experiment, we vary the cache size from very small (1 page) to enough to hold all the unique pages (100 pages), in order to see how each policy behaves over the range of cache sizes.

2OK, we cooked the results. But sometimes cooking is necessary to prove a point.

0 20 40 60 80 100 0%

20%

40%

60%

80%

100% The No-Locality Workload

Cache Size (Blocks)

Hit Rate

OPT LRU FIFO RAND

Figure 22.6: The No-Locality Workload

Figure 22.6 plots the results of the experiment for optimal, LRU, Random, and FIFO. The y-axis of the ﬁgure shows the hit rate that each policy achieves; the x-axis varies the cache size as described above.

We can draw a number of conclusions from the graph. First, when there is no locality in the workload, it doesn’t matter much which realistic policy you are using; LRU, FIFO, and Random all perform the same, with the hit rate exactly determined by the size of the cache. Second, when the cache is large enough to ﬁt the entire workload, it also doesn’t matter which policy you use; all policies (even Random) converge to a 100% hit rate when all the referenced blocks ﬁt in cache. Finally, you can see that optimal performs noticeably better than the realistic policies; peeking into the future, if it were possible, does a much better job of replacement.

The next workload we examine is called the “80-20” workload, which exhibits locality: 80% of the references are made to 20% of the pages (the “hot” pages); the remaining 20% of the references are made to the remaining 80% of the pages (the “cold” pages). In our workload, there are a total 100 unique pages again; thus, “hot” pages are referred to most of the time, and “cold” pages the remainder. Figure 22.7 (page 10) shows how the policies perform with this workload.

As you can see from the ﬁgure, while both random and FIFO do reasonably well, LRU does better, as it is more likely to hold onto the hot pages; as those pages have been referred to frequently in the past, they are likely to be referred to again in the near future. Optimal once again does better, showing that LRU’s historical information is not perfect.

EASY PIECES

0 20 40 60 80 100 0%

20%

40%

60%

80%

100% The 80-20 Workload

Cache Size (Blocks)

Hit Rate

OPT LRU FIFO RAND

Figure 22.7: The 80-20 Workload

You might now be wondering: is LRU’s improvement over Random and FIFO really that big of a deal? The answer, as usual, is “it depends.” If each miss is very costly (not uncommon), then even a small increase in hit rate (reduction in miss rate) can make a huge difference on performance. If misses are not so costly, then of course the beneﬁts possible with LRU are not nearly as important.

Let’s look at one ﬁnal workload. We call this one the “looping sequential” workload, as in it, we refer to 50 pages in sequence, starting at 0, then 1, ..., up to page 49, and then we loop, repeating those accesses, for a total of 10,000 accesses to 50 unique pages. The last graph in Figure 22.8 shows the behavior of the policies under this workload.

This workload, common in many applications (including important commercial applications such as databases [CD85]), represents a worstcase for both LRU and FIFO. These algorithms, under a looping-sequential workload, kick out older pages; unfortunately, due to the looping nature of the workload, these older pages are going to be accessed sooner than the pages that the policies prefer to keep in cache. Indeed, even with a cache of size 49, a looping-sequential workload of 50 pages results in a 0% hit rate. Interestingly, Random fares notably better, not quite approaching optimal, but at least achieving a non-zero hit rate. Turns out that random has some nice properties; one such property is not having weird corner-case behaviors.

0 20 40 60 80 100 0%

20%

40%

60%

80%

100% The Looping-Sequential Workload

Cache Size (Blocks)

Hit Rate

OPT LRU FIFO RAND

Figure 22.8: The Looping Workload

22.7 Implementing Historical Algorithms

As you can see, an algorithm such as LRU can generally do a better job than simpler policies like FIFO or Random, which may throw out important pages. Unfortunately, historical policies present us with a new challenge: how do we implement them?

Let’s take, for example, LRU. To implement it perfectly, we need to do a lot of work. Speciﬁcally, upon each page access (i.e., each memory access, whether an instruction fetch or a load or store), we must update some data structure to move this page to the front of the list (i.e., the MRU side). Contrast this to FIFO, where the FIFO list of pages is only accessed when a page is evicted (by removing the ﬁrst-in page) or when a new page is added to the list (to the last-in side). To keep track of which pages have been least- and most-recently used, the system has to do some accounting work on every memory reference. Clearly, without great care, such accounting could greatly reduce performance.

One method that could help speed this up is to add a little bit of hardware support. For example, a machine could update, on each page access, a time ﬁeld in memory (for example, this could be in the per-process page table, or just in some separate array in memory, with one entry per physical page of the system). Thus, when a page is accessed, the time ﬁeld would be set, by hardware, to the current time. Then, when replacing a page, the OS could simply scan all the time ﬁelds in the system to ﬁnd the least-recently-used page.

EASY PIECES

Unfortunately, as the number of pages in a system grows, scanning a huge array of times just to ﬁnd the absolute least-recently-used page is prohibitively expensive. Imagine a modern machine with 4GB of memory, chopped into 4KB pages. This machine has 1 million pages, and thus ﬁnding the LRU page will take a long time, even at modern CPU speeds. Which begs the question: do we really need to ﬁnd the absolute oldest page to replace? Can we instead survive with an approximation?

CRUX: HOW TO IMPLEMENT AN LRU REPLACEMENT POLICY Given that it will be expensive to implement perfect LRU, can we approximate it in some way, and still obtain the desired behavior?

22.8 Approximating LRU

As it turns out, the answer is yes: approximating LRU is more feasible from a computational-overhead standpoint, and indeed it is what many modern systems do. The idea requires some hardware support, in the form of a use bit (sometimes called the reference bit), the ﬁrst of which was implemented in the ﬁrst system with paging, the Atlas onelevel store [KE+62]. There is one use bit per page of the system, and the use bits live in memory somewhere (they could be in the per-process page tables, for example, or just in an array somewhere). Whenever a page is referenced (i.e., read or written), the use bit is set by hardware to 1. The hardware never clears the bit, though (i.e., sets it to 0); that is the responsibility of the OS.

How does the OS employ the use bit to approximate LRU? Well, there could be a lot of ways, but with the clock algorithm [C69], one simple approach was suggested. Imagine all the pages of the system arranged in a circular list. A clock hand points to some particular page to begin with (it doesn’t really matter which). When a replacement must occur, the OS checks if the currently-pointed to page P has a use bit of 1 or 0. If 1, this implies that page P was recently used and thus is not a good candidate for replacement. Thus, the use bit for P is set to 0 (cleared), and the clock hand is incremented to the next page (P + 1). The algorithm continues until it ﬁnds a use bit that is set to 0, implying this page has not been recently used (or, in the worst case, that all pages have been and that we have now searched through the entire set of pages, clearing all the bits).

Note that this approach is not the only way to employ a use bit to approximate LRU. Indeed, any approach which periodically clears the use bits and then differentiates between which pages have use bits of 1 versus 0 to decide which to replace would be ﬁne. The clock algorithm of Corbato’s was just one early approach which met with some success, and had the nice property of not repeatedly scanning through all of memory looking for an unused page.

0 20 40 60 80 100 0%

20%

40%

60%

80%

100% The 80-20 Workload

Cache Size (Blocks)

Hit Rate

OPT LRU FIFO RAND Clock

Figure 22.9: The 80-20 Workload With Clock

The behavior of a clock algorithm variant is shown in Figure 22.9. This variant randomly scans pages when doing a replacement; when it encounters a page with a reference bit set to 1, it clears the bit (i.e., sets it to 0); when it ﬁnds a page with the reference bit set to 0, it chooses it as its victim. As you can see, although it doesn’t do quite as well as perfect LRU, it does better than approaches that don’t consider history at all.

22.9 Considering Dirty Pages

One small modiﬁcation to the clock algorithm (also originally suggested by Corbato [C69]) that is commonly made is the additional consideration of whether a page has been modiﬁed or not while in memory. The reason for this: if a page has been modiﬁed and is thus dirty, it must be written back to disk to evict it, which is expensive. If it has not been modiﬁed (and is thus clean), the eviction is free; the physical frame can simply be reused for other purposes without additional I/O. Thus, some VM systems prefer to evict clean pages over dirty pages.

To support this behavior, the hardware should include a modiﬁed bit (a.k.a. dirty bit). This bit is set any time a page is written, and thus can be incorporated into the page-replacement algorithm. The clock algorithm, for example, could be changed to scan for pages that are both unused and clean to evict ﬁrst; failing to ﬁnd those, then for unused pages that are dirty, and so forth.

EASY PIECES

22.10 Other VM Policies

Page replacement is not the only policy the VM subsystem employs (though it may be the most important). For example, the OS also has to decide when to bring a page into memory. This policy, sometimes called the page selection policy (as it was called by Denning [D70]), presents the OS with some different options.

For most pages, the OS simply uses demand paging, which means the OS brings the page into memory when it is accessed, “on demand” as it were. Of course, the OS could guess that a page is about to be used, and thus bring it in ahead of time; this behavior is known as prefetching and should only be done when there is reasonable chance of success. For example, some systems will assume that if a code page P is brought into memory, that code page P +1 will likely soon be accessed and thus should be brought into memory too.

Another policy determines how the OS writes pages out to disk. Of course, they could simply be written out one at a time; however, many systems instead collect a number of pending writes together in memory and write them to disk in one (more efﬁcient) write. This behavior is usually called clustering or simply grouping of writes, and is effective because of the nature of disk drives, which perform a single large write more efﬁciently than many small ones.

22.11 Thrashing

Before closing, we address one ﬁnal question: what should the OS do when memory is simply oversubscribed, and the memory demands of the set of running processes simply exceeds the available physical memory? In this case, the system will constantly be paging, a condition sometimes referred to as thrashing [D70].

Some earlier operating systems had a fairly sophisticated set of mechanisms to both detect and cope with thrashing when it took place. For example, given a set of processes, a system could decide not to run a subset of processes, with the hope that the reduced set of processes’ working sets (the pages that they are using actively) ﬁt in memory and thus can make progress. This approach, generally known as admission control, states that it is sometimes better to do less work well than to try to do everything at once poorly, a situation we often encounter in real life as well as in modern computer systems (sadly).

Some current systems take more a draconian approach to memory overload. For example, some versions of Linux run an out-of-memory killer when memory is oversubscribed; this daemon chooses a memoryintensive process and kills it, thus reducing memory in a none-too-subtle manner. While successful at reducing memory pressure, this approach can have problems, if, for example, it kills the X server and thus renders any applications requiring the display unusable.

22.12 Summary

We have seen the introduction of a number of page-replacement (and other) policies, which are part of the VM subsystem of all modern operating systems. Modern systems add some tweaks to straightforward LRU approximations like clock; for example, scan resistance is an important part of many modern algorithms, such as ARC [MM03]. Scan-resistant algorithms are usually LRU-like but also try to avoid the worst-case behavior of LRU, which we saw with the looping-sequential workload. Thus, the evolution of page-replacement algorithms continues.

For many years, the importance of replacement algorithms had decreased, as the discrepancy between memory-access and disk-access times was so large. Speciﬁcally, because paging to disk was so expensive, the cost of frequent paging was prohibitive; simply put, no matter how good your replacement algorithm was, if you were performing frequent replacements, your system became unbearably slow. Thus, the best solution was a simple (if intellectually unsatisfying) one: buy more memory.

However, recent innovations in much faster storage devices (e.g., Flashbased SSDs) have changed these performance ratios yet again, leading to a renaissance in page replacement algorithms. See [SS10,W+21] for recent work in this space.

EASY PIECES
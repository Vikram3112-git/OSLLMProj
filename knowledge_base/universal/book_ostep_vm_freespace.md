# Free-Space Management (Operating Systems: Three Easy Pieces)

Source URL: https://pages.cs.wisc.edu/~remzi/OSTEP/vm-freespace.pdf
Source: Free-Space Management (Operating Systems: Three Easy Pieces)
Licence: Free online textbook by the authors; downloaded for personal study, not redistributed
Retrieved: 2026-10-23

Free-Space Management

In this chapter, we take a small detour from our discussion of virtualizing memory to discuss a fundamental aspect of any memory management system, whether it be a malloc library (managing pages of a process’s heap) or the OS itself (managing portions of the address space of a process). Speciﬁcally, we will discuss the issues surrounding free-space management.

Let us make the problem more speciﬁc. Managing free space can certainly be easy, as we will see when we discuss the concept of paging. It is easy when the space you are managing is divided into ﬁxed-sized units; in such a case, you just keep a list of these ﬁxed-sized units; when a client requests one of them, return the ﬁrst entry.

Where free-space management becomes more difﬁcult (and interesting) is when the free space you are managing consists of variable-sized units; this arises in a user-level memory-allocation library (as in malloc() and free()) and in an OS managing physical memory when using segmentation to implement virtual memory. In either case, the problem that exists is known as external fragmentation: the free space gets chopped into little pieces of different sizes and is thus fragmented; subsequent requests may fail because there is no single contiguous space that can satisfy the request, even though the total amount of free space exceeds the size of the request.

free used free 0 10 20 30

The ﬁgure shows an example of this problem. In this case, the total free space available is 20 bytes; unfortunately, it is fragmented into two chunks of size 10 each. As a result, a request for 15 bytes will fail even though there are 20 bytes free. And thus we arrive at the problem addressed in this chapter.

CRUX: HOW TO MANAGE FREE SPACE How should free space be managed, when satisfying variable-sized requests? What strategies can be used to minimize fragmentation? What are the time and space overheads of alternate approaches?

17.1 Assumptions

Most of this discussion will focus on the great history of allocators found in user-level memory-allocation libraries. We draw on Wilson’s excellent survey [W+95] but encourage interested readers to go to the source document itself for more details1.

We assume a basic interface such as that provided by malloc() and free(). Speciﬁcally, void *malloc(size t size) takes a single parameter, size, which is the number of bytes requested by the application; it hands back a pointer (of no particular type, or a void pointer in C lingo) to a region of that size (or greater). The complementary routine void free(void *ptr) takes a pointer and frees the corresponding chunk. Note the implication of the interface: the user, when freeing the space, does not inform the library of its size; thus, the library must be able to ﬁgure out how big a chunk of memory is when handed just a pointer to it. We’ll discuss how to do this a bit later on in the chapter.

The space that this library manages is known historically as the heap, and the generic data structure used to manage free space in the heap is some kind of free list. This structure contains references to all of the free chunks of space in the managed region of memory. Of course, this data structure need not be a list per se, but just some kind of data structure to track free space.

We further assume that primarily we are concerned with external fragmentation, as described above. Allocators could of course also have the problem of internal fragmentation; if an allocator hands out chunks of memory bigger than that requested, any unasked for (and thus unused) space in such a chunk is considered internal fragmentation (because the waste occurs inside the allocated unit) and is another example of space waste. However, for the sake of simplicity, and because it is the more interesting of the two types of fragmentation, we’ll mostly focus on external fragmentation.

We’ll also assume that once memory is handed out to a client, it cannot be relocated to another location in memory. For example, if a program calls malloc() and is given a pointer to some space within the heap, that memory region is essentially “owned” by the program (and cannot be moved by the library) until the program returns it via a corresponding call to free(). Thus, no compaction of free space is possible, which

1It is nearly 80 pages long; thus, you really have to be interested!

would be useful to combat fragmentation2. Compaction could, however, be used in the OS to deal with fragmentation when implementing segmentation (as discussed in said chapter on segmentation).

Finally, we’ll assume that the allocator manages a contiguous region of bytes. In some cases, an allocator could ask for that region to grow; for example, a user-level memory-allocation library might call into the kernel to grow the heap (via a system call such as sbrk) when it runs out of space. However, for simplicity, we’ll just assume that the region is a single ﬁxed size throughout its life.

17.2 Low-level Mechanisms

Before delving into some policy details, we’ll ﬁrst cover some common mechanisms used in most allocators. First, we’ll discuss the basics of splitting and coalescing, common techniques in most any allocator. Second, we’ll show how one can track the size of allocated regions quickly and with relative ease. Finally, we’ll discuss how to build a simple list inside the free space to keep track of what is free and what isn’t.

Splitting and Coalescing

A free list contains a set of elements that describe the free space still remaining in the heap. Thus, assume the following 30-byte heap:

free used free 0 10 20 30

The free list for this heap would have two elements on it. One entry describes the ﬁrst 10-byte free segment (bytes 0-9), and one entry describes the other free segment (bytes 20-29):

head addr:0 len:10

addr:20

len:10 NULL

As described above, a request for anything greater than 10 bytes will fail (returning NULL); there just isn’t a single contiguous chunk of memory of that size available. A request for exactly that size (10 bytes) could be satisﬁed easily by either of the free chunks. But what happens if the request is for something smaller than 10 bytes?

Assume we have a request for just a single byte of memory. In this case, the allocator will perform an action known as splitting: it will ﬁnd

2Once you hand a pointer to a chunk of memory to a C program, it is generally difﬁcult to determine all references (pointers) to that region, which may be stored in other variables or even in registers at a given point in execution. This may not be the case in more stronglytyped, garbage-collected languages, which would thus enable compaction as a technique to combat fragmentation.

EASY PIECES

a free chunk of memory that can satisfy the request and split it into two. The ﬁrst chunk it will return to the caller; the second chunk will remain on the list. Thus, in our example above, if a request for 1 byte were made, and the allocator decided to use the second of the two elements on the list to satisfy the request, the call to malloc() would return 20 (the address of the 1-byte allocated region) and the list would end up looking like this:

head addr:0 len:10

addr:21

len:9 NULL

In the picture, you can see the list basically stays intact; the only change is that the free region now starts at 21 instead of 20, and the length of that free region is now just 93. Thus, the split is commonly used in allocators when requests are smaller than the size of any particular free chunk.

A corollary mechanism found in many allocators is known as coalescing of free space. Take our example from above once more (free 10 bytes, used 10 bytes, and another free 10 bytes).

Given this (tiny) heap, what happens when an application calls free(10), thus returning the space in the middle of the heap? If we simply add this free space back into our list without too much thinking, we might end up with a list that looks like this:

head addr:10

len:10

addr:0 len:10

addr:20

len:10 NULL

Note the problem: while the entire heap is now free, it is seemingly divided into three chunks of 10 bytes each. Thus, if a user requests 20 bytes, a simple list traversal will not ﬁnd such a free chunk, and return failure.

What allocators do in order to avoid this problem is coalesce free space when a chunk of memory is freed. The idea is simple: when returning a free chunk in memory, look carefully at the addresses of the chunk you are returning as well as the nearby chunks of free space; if the newlyfreed space sits right next to one (or two, as in this example) existing free chunks, merge them into a single larger free chunk. Thus, with coalescing, our ﬁnal list should look like this:

head addr:0 len:30 NULL

Indeed, this is what the heap list looked like at ﬁrst, before any allocations were made. With coalescing, an allocator can better ensure that large free extents are available for the application.

3This discussion assumes that there are no headers, an unrealistic but simplifying assumption we make for now.

ptr

The header used by malloc library

The 20 bytes returned to caller

Figure 17.1: An Allocated Region Plus Header

size: 20

magic: 1234567

hptr

ptr

The 20 bytes returned to caller

Figure 17.2: Speciﬁc Contents Of The Header

Tracking The Size Of Allocated Regions

You might have noticed that the interface to free(void *ptr) does not take a size parameter; thus it is assumed that given a pointer, the malloc library can quickly determine the size of the region of memory being freed and thus incorporate the space back into the free list.

To accomplish this task, most allocators store a little bit of extra information in a header block which is kept in memory, usually just before the handed-out chunk of memory. Let’s look at an example again (Figure 17.1). In this example, we are examining an allocated block of size 20 bytes, pointed to by ptr; imagine the user called malloc() and stored the results in ptr, e.g., ptr = malloc(20);.

The header minimally contains the size of the allocated region (in this case, 20); it may also contain additional pointers to speed up deallocation, a magic number to provide additional integrity checking, and other information. Let’s assume a simple header which contains the size of the region and a magic number, like this:

typedef struct {

int size; int magic; } header_t;

EASY PIECES

The example above would look like what you see in Figure 17.2. When the user calls free(ptr), the library then uses simple pointer arithmetic to ﬁgure out where the header begins:

void free(void *ptr) {

header_t *hptr = (header_t *) ptr - 1; ...

After obtaining such a pointer to the header, the library can easily determine whether the magic number matches the expected value as a sanity check (assert(hptr->magic == 1234567)) and calculate the total size of the newly-freed region via simple math (i.e., adding the size of the header to size of the region). Note the small but critical detail in the last sentence: the size of the free region is the size of the header plus the size of the space allocated to the user. Thus, when a user requests N bytes of memory, the library does not search for a free chunk of size N; rather, it searches for a free chunk of size N plus the size of the header.

Embedding A Free List

Thus far we have treated our simple free list as a conceptual entity; it is just a list describing the free chunks of memory in the heap. But how do we build such a list inside the free space itself?

In a more typical list, when allocating a new node, you would just call malloc() when you need space for the node. Unfortunately, within the memory-allocation library, you can’t do this! Instead, you need to build the list inside the free space itself. Don’t worry if this sounds a little weird; it is, but not so weird that you can’t do it!

Assume we have a 4096-byte chunk of memory to manage (i.e., the heap is 4KB). To manage this as a free list, we ﬁrst have to initialize said list; initially, the list should have one entry, of size 4096 (minus the header size). Here is the description of a node of the list:

typedef struct __node_t {

int size; struct __node_t *next; } node_t;

Now let’s look at some code that initializes the heap and puts the ﬁrst element of the free list inside that space. We are assuming that the heap is built within some free space acquired via a call to the system call mmap(); this is not the only way to build such a heap but serves us well in this example. Here is the code:

// mmap() returns a pointer to a chunk of free space node_t *head = mmap(NULL, 4096, PROT_READ|PROT_WRITE,

MAP_ANON|MAP_PRIVATE, -1, 0); head->size = 4096 - sizeof(node_t); head->next = NULL;

size: 4088

next: 0

...

head [virtual address: 16KB] header: size field

header: next field (NULL is 0)

the rest of the 4KB chunk

Figure 17.3: A Heap With One Free Chunk

size: 100

magic: 1234567

. . .

size: 3980

next: 0

. . .

ptr

[virtual address: 16KB]

head

The 100 bytes now allocated

The free 3980 byte chunk

Figure 17.4: A Heap: After One Allocation

After running this code, the status of the list is that it has a single entry, of size 4088. Yes, this is a tiny heap, but it serves as a ﬁne example for us here. The head pointer contains the beginning address of this range; let’s assume it is 16KB (though any virtual address would be ﬁne). Visually, the heap thus looks like what you see in Figure 17.3.

Now, let’s imagine that a chunk of memory is requested, say of size 100 bytes. To service this request, the library will ﬁrst ﬁnd a chunk that is large enough to accommodate the request; because there is only one free chunk (size: 4088), this chunk will be chosen. Then, the chunk will be split into two: one chunk big enough to service the request (and header, as described above), and the remaining free chunk. Assuming an 8-byte header (an integer size and an integer magic number), the space in the heap now looks like what you see in Figure 17.4.

Thus, upon the request for 100 bytes, the library allocated 108 bytes

EASY PIECES

size: 100

magic: 1234567

. . .

size: 100

magic: 1234567

. . .

size: 100

magic: 1234567

. . .

size: 3764

next: 0

. . .

sptr

[virtual address: 16KB]

head

100 bytes still allocated

100 bytes still allocated (but about to be freed)

100-bytes still allocated

The free 3764-byte chunk

Figure 17.5: Free Space With Three Chunks Allocated out of the existing one free chunk, returns a pointer (marked ptr in the ﬁgure above) to it, stashes the header information immediately before the allocated space for later use upon free(), and shrinks the one free node in the list to 3980 bytes (4088 minus 108).

Now let’s look at the heap when there are three allocated regions, each of 100 bytes (or 108 including the header). A visualization of this heap is shown in Figure 17.5.

As you can see therein, the ﬁrst 324 bytes of the heap are now allocated, and thus we see three headers in that space as well as three 100byte regions being used by the calling program. The free list remains uninteresting: just a single node (pointed to by head), but now only 3764

size: 100

magic: 1234567

. . .

size: 100

next: 16708

. . .

size: 100

magic: 1234567

. . .

size: 3764

next: 0

. . .

[virtual address: 16KB]

head

sptr

100 bytes still allocated

(now a free chunk of memory)

100-bytes still allocated

The free 3764-byte chunk

Figure 17.6: Free Space With Two Chunks Allocated

bytes in size after the three splits. But what happens when the calling program returns some memory via free()?

In this example, the application returns the middle chunk of allocated memory, by calling free(16500) (the value 16500 is arrived upon by adding the start of the memory region, 16384, to the 108 of the previous chunk and the 8 bytes of the header for this chunk). This value is shown in the previous diagram by the pointer sptr.

The library immediately ﬁgures out the size of the free region, and then adds the free chunk back onto the free list. Assuming we insert at the head of the free list, the space now looks like this (Figure 17.6).

EASY PIECES

size: 100

next: 16492

. . .

size: 100

next: 16708

. . .

size: 100

next: 16384

. . .

size: 3764

next: 0

. . .

[virtual address: 16KB]

head

(now free)

(now free)

(now free)

The free 3764-byte chunk

Figure 17.7: A Non-Coalesced Free List Now we have a list that starts with a small free chunk (100 bytes, pointed to by the head of the list) and a large free chunk (3764 bytes). Our list ﬁnally has more than one element on it! And yes, the free space is fragmented, an unfortunate but common occurrence.

One last example: let’s assume now that the last two in-use chunks are freed. Without coalescing, you end up with fragmentation (Figure 17.7).

As you can see from the ﬁgure, we now have a big mess! Why? Simple, we forgot to coalesce the list. Although all of the memory is free, it is chopped up into pieces, thus appearing as a fragmented memory despite not being one. The solution is simple: go through the list and merge neighboring chunks; when ﬁnished, the heap will be whole again.

Growing The Heap

We should discuss one last mechanism found within many allocation libraries. Speciﬁcally, what should you do if the heap runs out of space? The simplest approach is just to fail. In some cases this is the only option, and thus returning NULL is an honorable approach. Don’t feel bad! You tried, and though you failed, you fought the good ﬁght.

Most traditional allocators start with a small-sized heap and then request more memory from the OS when they run out. Typically, this means they make some kind of system call (e.g., sbrk in most UNIX systems) to grow the heap, and then allocate the new chunks from there. To service the sbrk request, the OS ﬁnds free physical pages, maps them into the address space of the requesting process, and then returns the value of the end of the new heap; at that point, a larger heap is available, and the request can be successfully serviced.

17.3 Basic Strategies

Now that we have some machinery under our belt, let’s go over some basic strategies for managing free space. These approaches are mostly based on pretty simple policies that you could think up yourself; try it before reading and see if you come up with all of the alternatives (or maybe some new ones!).

The ideal allocator is both fast and minimizes fragmentation. Unfortunately, because the stream of allocation and free requests can be arbitrary (after all, they are determined by the programmer), any particular strategy can do quite badly given the wrong set of inputs. Thus, we will not describe a “best” approach, but rather talk about some basics and discuss their pros and cons.

Best Fit

The best ﬁt strategy is quite simple: ﬁrst, search through the free list and ﬁnd chunks of free memory that are as big or bigger than the requested size. Then, return the one that is the smallest in that group of candidates; this is the so called best-ﬁt chunk (it could be called smallest ﬁt too). One pass through the free list is enough to ﬁnd the correct block to return.

The intuition behind best ﬁt is simple: by returning a block that is close to what the user asks, best ﬁt tries to reduce wasted space. However, there is a cost; naive implementations pay a heavy performance penalty when performing an exhaustive search for the correct free block.

Worst Fit

The worst ﬁt approach is the opposite of best ﬁt; ﬁnd the largest chunk and return the requested amount; keep the remaining (large) chunk on the free list. Worst ﬁt tries to thus leave big chunks free instead of lots of

EASY PIECES

small chunks that can arise from a best-ﬁt approach. Once again, however, a full search of free space is required, and thus this approach can be costly. Worse, most studies show that it performs badly, leading to excess fragmentation while still having high overheads.

First Fit

The ﬁrst ﬁt method simply ﬁnds the ﬁrst block that is big enough and returns the requested amount to the user. As before, the remaining free space is kept free for subsequent requests.

First ﬁt has the advantage of speed — no exhaustive search of all the free spaces are necessary — but sometimes pollutes the beginning of the free list with small objects. Thus, how the allocator manages the free list’s order becomes an issue. One approach is to use address-based ordering; by keeping the list ordered by the address of the free space, coalescing becomes easier, and fragmentation tends to be reduced.

Next Fit

Instead of always beginning the ﬁrst-ﬁt search at the beginning of the list, the next ﬁt algorithm keeps an extra pointer to the location within the list where one was looking last. The idea is to spread the searches for free space throughout the list more uniformly, thus avoiding splintering of the beginning of the list. The performance of such an approach is quite similar to ﬁrst ﬁt, as an exhaustive search is once again avoided.

Examples

Here are a few examples of the above strategies. Envision a free list with three elements on it, of sizes 10, 30, and 20 (we’ll ignore headers and other details here, instead just focusing on how strategies operate):

head 10 30 20 NULL

Assume an allocation request of size 15. A best-ﬁt approach would search the entire list and ﬁnd that 20 was the best ﬁt, as it is the smallest free space that can accommodate the request. The resulting free list:

head 10 30 5 NULL

As happens in this example, and often happens with a best-ﬁt approach, a small free chunk is now left over. A worst-ﬁt approach is similar but instead ﬁnds the largest chunk, in this example 30. The resulting list:

head 10 15 20 NULL

The ﬁrst-ﬁt strategy, in this example, does the same thing as worst-ﬁt, also ﬁnding the ﬁrst free block that can satisfy the request. The difference is in the search cost; both best-ﬁt and worst-ﬁt look through the entire list; ﬁrst-ﬁt only examines free chunks until it ﬁnds one that ﬁts, thus reducing search cost.

These examples just scratch the surface of allocation policies. More detailed analysis with real workloads and more complex allocator behaviors (e.g., coalescing) are required for a deeper understanding. Perhaps something for a homework section, you say?

17.4 Other Approaches

Beyond the basic approaches described above, there have been a host of suggested techniques and algorithms to improve memory allocation in some way. We list a few of them here for your consideration (i.e., to make you think about a little more than just best-ﬁt allocation).

Segregated Lists

One interesting approach that has been around for some time is the use of segregated lists. The basic idea is simple: if a particular application has one (or a few) popular-sized request that it makes, keep a separate list just to manage objects of that size; all other requests are forwarded to a more general memory allocator.

The beneﬁts of such an approach are obvious. By having a chunk of memory dedicated for one particular size of requests, fragmentation is much less of a concern; moreover, allocation and free requests can be served quite quickly when they are of the right size, as no complicated search of a list is required.

Just like any good idea, this approach introduces new complications into a system as well. For example, how much memory should one dedicate to the pool of memory that serves specialized requests of a given size, as opposed to the general pool? One particular allocator, the slab allocator by uber-engineer Jeff Bonwick (which was designed for use in the Solaris kernel), handles this issue in a rather nice way [B94].

Speciﬁcally, when the kernel boots up, it allocates a number of object caches for kernel objects that are likely to be requested frequently (such as locks, ﬁle-system inodes, etc.); the object caches thus are each segregated free lists of a given size and serve memory allocation and free requests quickly. When a given cache is running low on free space, it requests some slabs of memory from a more general memory allocator (the total amount requested being a multiple of the page size and the object in question). Conversely, when the reference counts of the objects within a given slab all go to zero, the general allocator can reclaim them from the specialized allocator, which is often done when the VM system needs more memory.

EASY PIECES

ASIDE: GREAT ENGINEERS ARE REALLY GREAT Engineers like Jeff Bonwick (who not only wrote the slab allocator mentioned herein but also was the lead of an amazing ﬁle system, ZFS) are the heart of Silicon Valley. Behind almost any great product or technology is a human (or small group of humans) who are way above average in their talents, abilities, and dedication. As Mark Zuckerberg (of Facebook) says: “Someone who is exceptional in their role is not just a little better than someone who is pretty good. They are 100 times better.” This is why, still today, one or two people can start a company that changes the face of the world forever (think Google, Apple, or Facebook). Work hard and you might become such a “100x” person as well! Failing that, ﬁnd a way to work with such a person; you’ll learn more in a day than most learn in a month.

The slab allocator also goes beyond most segregated list approaches by keeping free objects on the lists in a pre-initialized state. Bonwick shows that initialization and destruction of data structures is costly [B94]; by keeping freed objects in a particular list in their initialized state, the slab allocator thus avoids frequent initialization and destruction cycles per object and thus lowers overheads noticeably.

Buddy Allocation

Because coalescing is critical for an allocator, some approaches have been designed around making coalescing simple. One good example is found in the binary buddy allocator [K65].

In such a system, free memory is ﬁrst conceptually thought of as one big space of size 2N. When a request for memory is made, the search for free space recursively divides free space by two until a block that is big enough to accommodate the request is found (and a further split into two would result in a space that is too small). At this point, the requested block is returned to the user. Here is an example of a 64KB free space getting divided in the search for a 7KB block (Figure 17.8, page 15).

In the example, the leftmost 8KB block is allocated (as indicated by the darker shade of gray) and returned to the user; note that this scheme can suffer from internal fragmentation, as you are only allowed to give out power-of-two-sized blocks.

The beauty of buddy allocation is found in what happens when that block is freed. When returning the 8KB block to the free list, the allocator checks whether the “buddy” 8KB is free; if so, it coalesces the two blocks into a 16KB block. The allocator then checks if the buddy of the 16KB block is still free; if so, it coalesces those two blocks. This recursive coalescing process continues up the tree, either restoring the entire free space or stopping when a buddy is found to be in use.

32 KB 32 KB

16 KB 16 KB

8 KB 8 KB

Figure 17.8: Example Buddy-managed Heap The reason buddy allocation works so well is that it is simple to determine the buddy of a particular block. How, you ask? Think about the addresses of the blocks in the free space above. If you think carefully enough, you’ll see that the address of each buddy pair only differs by a single bit; which bit is determined by the level in the buddy tree. And thus you have a basic idea of how binary buddy allocation schemes work. For more detail, as always, see the Wilson survey [W+95].

Other Ideas One major problem with many of the approaches described above is their lack of scaling. Speciﬁcally, searching lists can be quite slow. Thus, advanced allocators use more complex data structures to address these costs, trading simplicity for performance. Examples include balanced binary trees, splay trees, or partially-ordered trees [W+95].

Given that modern systems often have multiple processors and run multi-threaded workloads (something you’ll learn about in great detail in the section of the book on Concurrency), it is not surprising that a lot of effort has been spent making allocators work well on multiprocessorbased systems. Two wonderful examples are found in Berger et al. [B+00] and Evans [E06]; check them out for the details.

These are but two of the thousands of ideas people have had over time about memory allocators; read on your own if you are curious. Failing that, read about how the glibc allocator works [S15], to give you a sense of what the real world is like.

17.5 Summary

In this chapter, we’ve discussed the most rudimentary forms of memory allocators. Such allocators exist everywhere, linked into every C program you write, as well as in the underlying OS which is managing memory for its own data structures. As with many systems, there are many

EASY PIECES

trade-offs to be made in building such a system, and the more you know about the exact workload presented to an allocator, the more you could do to tune it to work better for that workload. Making a fast, space-efﬁcient, scalable allocator that works well for a broad range of workloads remains an on-going challenge in modern computer systems.
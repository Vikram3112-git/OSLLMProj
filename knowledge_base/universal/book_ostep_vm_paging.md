# Paging: Introduction (Operating Systems: Three Easy Pieces)

Source URL: https://pages.cs.wisc.edu/~remzi/OSTEP/vm-paging.pdf
Source: Paging: Introduction (Operating Systems: Three Easy Pieces)
Licence: Free online textbook by the authors; downloaded for personal study, not redistributed
Retrieved: 2026-10-23

Paging: Introduction

It is sometimes said that the operating system takes one of two approaches when solving most any space-management problem. The ﬁrst approach is to chop things up into variable-sized pieces, as we saw with segmentation in virtual memory. Unfortunately, this solution has inherent difﬁculties. In particular, when dividing a space into different-size chunks, the space itself can become fragmented, and thus allocation becomes more challenging over time.

Thus, it may be worth considering the second approach: to chop up space into ﬁxed-sized pieces. In virtual memory, we call this idea paging, and it goes back to an early and important system, the Atlas [KE+62, L78]. Instead of splitting up a process’s address space into some number of variable-sized logical segments (e.g., code, heap, stack), we divide it into ﬁxed-sized units, each of which we call a page. Correspondingly, we view physical memory as an array of ﬁxed-sized slots called page frames; each of these frames can contain a single virtual-memory page. Our challenge:

THE CRUX: HOW TO VIRTUALIZE MEMORY WITH PAGES How can we virtualize memory with pages, so as to avoid the problems of segmentation? What are the basic techniques? How do we make those techniques work well, with minimal space and time overheads?

18.1 A Simple Example And Overview

To help make this approach more clear, let’s illustrate it with a simple example. Figure 18.1 (page 2) presents an example of a tiny address space, only 64 bytes total in size, with four 16-byte pages (virtual pages 0, 1, 2, and 3). Real address spaces are much bigger, of course, commonly 32 bits and thus 4-GB of address space, or even 64 bits1; in the book, we’ll often use tiny examples to make them easier to digest.

1A 64-bit address space is hard to imagine, it is so amazingly large. An analogy might help: if you think of a 32-bit address space as the size of a tennis court, a 64-bit address space is about the size of Europe(!).

(page 3)

(page 2)

(page 1)

(page 0 of the address space)

Figure 18.1: A Simple 64-byte Address Space Physical memory, as shown in Figure 18.2, also consists of a number of ﬁxed-sized slots, in this case eight page frames (making for a 128-byte physical memory, also ridiculously small). As you can see in the diagram, the pages of the virtual address space have been placed at different locations throughout physical memory; the diagram also shows the OS using some of physical memory for itself.

Paging, as we will see, has a number of advantages over our previous approaches. Probably the most important improvement will be ﬂexibility: with a fully-developed paging approach, the system will be able to support the abstraction of an address space effectively, regardless of how a process uses the address space; we won’t, for example, make assumptions about the direction the heap and stack grow and how they are used.

page frame 7

page frame 6

page frame 5

page frame 4

page frame 3

page frame 2

page frame 1

page frame 0 of physical memory reserved for OS

(unused)

page 3 of AS

page 0 of AS

(unused)

page 2 of AS

(unused)

page 1 of AS

Figure 18.2: A 64-Byte Address Space In A 128-Byte Physical Memory

Another advantage is the simplicity of free-space management that paging affords. For example, when the OS wishes to place our tiny 64-byte address space into our eight-page physical memory, it simply ﬁnds four free pages; perhaps the OS keeps a free list of all free pages for this, and just grabs the ﬁrst four free pages off of this list. In the example, the OS has placed virtual page 0 of the address space (AS) in physical frame 3, virtual page 1 of the AS in physical frame 7, page 2 in frame 5, and page 3 in frame 2. Page frames 1, 4, and 6 are currently free. To record where each virtual page of the address space is placed in physical memory, the operating system usually keeps a per-process data structure known as a page table. The major role of the page table is to store address translations for each of the virtual pages of the address space, thus letting us know where in physical memory each page resides. For our simple example (Figure 18.2, page 2), the page table would thus have the following four entries: (Virtual Page 0 →Physical Frame 3), (VP 1 →PF 7), (VP 2 →PF 5), and (VP 3 →PF 2).

It is important to remember that this page table is a per-process data structure (most page table structures we discuss are per-process structures; an exception we’ll touch on is the inverted page table). If another process were to run in our example above, the OS would have to manage a different page table for it, as its virtual pages obviously map to different physical pages (modulo any sharing going on).

Now, we know enough to perform an address-translation example. Let’s imagine the process with that tiny address space (64 bytes) is performing a memory access:

movl <virtual address>, %eax

Speciﬁcally, let’s pay attention to the explicit load of the data from address <virtual address> into the register eax (and thus ignore the instruction fetch that must have happened prior).

To translate this virtual address that the process generated, we have to ﬁrst split it into two components: the virtual page number (VPN), and the offset within the page. For this example, because the virtual address space of the process is 64 bytes, we need 6 bits total for our virtual address (26 = 64). Thus, our virtual address can be conceptualized as follows:

Va5 Va4 Va3 Va2 Va1 Va0

In this diagram, Va5 is the highest-order bit of the virtual address, and Va0 the lowest-order bit. Because we know the page size (16 bytes), we can further divide the virtual address as follows:

Va5 Va4 Va3 Va2 Va1 Va0

VPN offset

EASY PIECES

The page size is 16 bytes in a 64-byte address space; thus we need to be able to select 4 pages, and the top 2 bits of the address do just that. Thus, we have a 2-bit virtual page number (VPN). The remaining bits tell us which byte of the page we are interested in, 4 bits in this case; we call this the offset.

When a process generates a virtual address, the OS and hardware must combine to translate it into a meaningful physical address. For example, let us assume the load above was to virtual address 21:

movl 21, %eax

Turning “21” into binary form, we get “010101”, and thus we can examine this virtual address and see how it breaks down into a virtual page number (VPN) and offset:

0 1 0 1 0 1

VPN offset

Thus, the virtual address “21” is on the 5th (“0101”th) byte of virtual page “01” (or 1). With our virtual page number, we can now index our page table and ﬁnd which physical frame virtual page 1 resides within. In the page table above the physical frame number (PFN) (also sometimes called the physical page number or PPN) is 7 (binary 111). Thus, we can translate this virtual address by replacing the VPN with the PFN and then issue the load to physical memory (Figure 18.3).

0 1 0 1 0 1

VPN offset

1 1 1 0 1 0 1

Address Translation

PFN offset

Virtual Address

Physical Address

Figure 18.3: The Address Translation Process

page frame 7

page frame 6

page frame 5

page frame 4

page frame 3

page frame 2

page frame 1

page frame 0 of physical memory

(unused)

page 3 of AS

page 0 of AS

(unused)

page 2 of AS

(unused)

page 1 of AS

page table:

3 7 5 2

Figure 18.4: Example: Page Table in Kernel Physical Memory

Note the offset stays the same (i.e., it is not translated), because the offset just tells us which byte within the page we want. Our ﬁnal physical address is 1110101 (117 in decimal), and is exactly where we want our load to fetch data from (Figure 18.2, page 2).

With this basic overview in mind, we can now ask (and hopefully, answer) a few basic questions you may have about paging. For example, where are these page tables stored? What are the typical contents of the page table, and how big are the tables? Does paging make the system (too) slow? These and other beguiling questions are answered, at least in part, in the text below. Read on!

18.2 Where Are Page Tables Stored?

Page tables can get terribly large, much bigger than the small segment table or base/bounds pair we have discussed previously. For example, imagine a typical 32-bit address space, with 4KB pages. This virtual address splits into a 20-bit VPN and 12-bit offset (recall that 10 bits would be needed for a 1KB page size, and just add two more to get to 4KB).

A 20-bit VPN implies that there are 220 translations that the OS would have to manage for each process (that’s roughly a million); assuming we need 4 bytes per page table entry (PTE) to hold the physical translation plus any other useful stuff, we get an immense 4MB of memory needed for each page table! That is pretty large. Now imagine there are 100 processes running: this means the OS would need 400MB of memory just for all those address translations! Even in the modern era, where

EASY PIECES

ASIDE: DATA STRUCTURE — THE PAGE TABLE One of the most important data structures in the memory management subsystem of a modern OS is the page table. In general, a page table stores virtual-to-physical address translations, thus letting the system know where each page of an address space actually resides in physical memory. Because each address space requires such translations, in general there is one page table per process in the system. The exact structure of the page table is either determined by the hardware (older systems) or can be more ﬂexibly managed by the OS (modern systems).

machines have gigabytes of memory, it seems a little crazy to use a large chunk of it just for translations, no? And we won’t even think about how big such a page table would be for a 64-bit address space; that would be too gruesome and perhaps scare you off entirely.

Because page tables are so big, we don’t keep any special on-chip hardware in the MMU to store the page table of the currently-running process. Instead, we store the page table for each process in memory somewhere. Let’s assume for now that the page tables live in physical memory that the OS manages; later we’ll see that much of OS memory itself can be virtualized, and thus page tables can be stored in OS virtual memory (and even swapped to disk), but that is too confusing right now, so we’ll ignore it. In Figure 18.4 (page 5) is a picture of a page table in OS memory; see the tiny set of translations in there?

18.3 What’s Actually In The Page Table?

Let’s talk a little about page table organization. The page table is just a data structure that is used to map virtual addresses (or really, virtual page numbers) to physical addresses (physical frame numbers). Thus, any data structure could work. The simplest form is called a linear page table, which is just an array. The OS indexes the array by the virtual page number (VPN), and looks up the page-table entry (PTE) at that index in order to ﬁnd the desired physical frame number (PFN). For now, we will assume this simple linear structure; in later chapters, we will make use of more advanced data structures to help solve some problems with paging.

As for the contents of each PTE, we have a number of different bits in there worth understanding at some level. A valid bit is common to indicate whether the particular translation is valid; for example, when a program starts running, it will have code and heap at one end of its address space, and the stack at the other. All the unused space in-between will be marked invalid, and if the process tries to access such memory, it will generate a trap to the OS which will likely terminate the process. Thus, the valid bit is crucial for supporting a sparse address space; by simply marking all the unused pages in the address space invalid, we remove the need to allocate physical frames for those pages and thus save a great deal of memory.

31 12 11 9 8 7 6 5 4 3 2 1 0

PFN

G

PAT

D

A

PCD

PWT

U/S

R/W

P

Figure 18.5: An x86 Page Table Entry (PTE) We also might have protection bits, indicating whether the page could be read from, written to, or executed from. Again, accessing a page in a way not allowed by these bits will generate a trap to the OS.

There are a couple of other bits that are important but we won’t talk about much for now. A present bit indicates whether this page is in physical memory or on disk (i.e., it has been swapped out). We will understand this machinery further when we study how to swap parts of the address space to disk to support address spaces that are larger than physical memory; swapping allows the OS to free up physical memory by moving rarely-used pages to disk. A dirty bit is also common, indicating whether the page has been modiﬁed since it was brought into memory.

A reference bit (a.k.a. accessed bit) is sometimes used to track whether a page has been accessed, and is useful in determining which pages are popular and thus should be kept in memory; such knowledge is critical during page replacement, a topic we will study in great detail in subsequent chapters.

Figure 18.5 shows an example page table entry from the x86 architecture [I09]. It contains a present bit (P); a read/write bit (R/W) which determines if writes are allowed to this page; a user/supervisor bit (U/S) which determines if user-mode processes can access the page; a few bits (PWT, PCD, PAT, and G) that determine how hardware caching works for these pages; an accessed bit (A) and a dirty bit (D); and ﬁnally, the page frame number (PFN) itself.

Read the Intel Architecture Manuals [I09] for more details on x86 paging support. Be forewarned, however; reading manuals such as these, while quite informative (and certainly necessary for those who write code to use such page tables in the OS), can be challenging at ﬁrst. A little patience, and a lot of desire, is required.

ASIDE: WHY NO VALID BIT? You may notice that in the Intel example, there are no separate valid and present bits, but rather just a present bit (P). If that bit is set (P=1), it means the page is both present and valid. If not (P=0), it means that the page may not be present in memory (but is valid), or may not be valid. An access to a page with P=0 will trigger a trap to the OS; the OS must then use additional structures it keeps to determine whether the page is valid (and thus perhaps should be swapped back in) or not (and thus the program is attempting to access memory illegally). This sort of judiciousness is common in hardware, which often just provide the minimal set of features upon which the OS can build a full service.

EASY PIECES

18.4 Paging: Also Too Slow

With page tables in memory, we already know that they might be too big. As it turns out, they can slow things down too. For example, take our simple instruction:

movl 21, %eax

Again, let’s just examine the explicit reference to address 21 and not worry about the instruction fetch. In this example, we’ll assume the hardware performs the translation for us. To fetch the desired data, the system must ﬁrst translate the virtual address (21) into the correct physical address (117). Thus, before fetching the data from address 117, the system must ﬁrst fetch the proper page table entry from the process’s page table, perform the translation, and then load the data from physical memory.

To do so, the hardware must know where the page table is for the currently-running process. Let’s assume for now that a single page-table base register contains the physical address of the starting location of the page table. To ﬁnd the location of the desired PTE, the hardware will thus perform the following functions:

VPN = (VirtualAddress & VPN_MASK) >> SHIFT PTEAddr = PageTableBaseRegister + (VPN * sizeof(PTE))

In our example, VPN_MASK would be set to 0x30 (hex 30, or binary 110000) which picks out the VPN bits from the full virtual address; SHIFT is set to 4 (the number of bits in the offset), such that we move the VPN bits down to form the correct integer virtual page number. For example, with virtual address 21 (010101), and masking turns this value into 010000; the shift turns it into 01, or virtual page 1, as desired. We then use this value as an index into the array of PTEs pointed to by the page table base register.

Once this physical address is known, the hardware can fetch the PTE from memory, extract the PFN, and concatenate it with the offset from the virtual address to form the desired physical address. Speciﬁcally, you can think of the PFN being left-shifted by SHIFT, and then bitwise OR’d with the offset to form the ﬁnal address as follows:

offset = VirtualAddress & OFFSET_MASK PhysAddr = (PFN << SHIFT) | offset

Finally, the hardware can fetch the desired data from memory and put it into register eax. The program has now succeeded at loading a value from memory!

To summarize, we now describe the initial protocol for what happens on each memory reference. Figure 18.6 (page 9) shows the approach. For every memory reference (whether an instruction fetch or an explicit load or store), paging requires us to perform one extra memory reference in order to ﬁrst fetch the translation from the page table. That is a lot of

1 // Extract the VPN from the virtual address

2 VPN = (VirtualAddress & VPN_MASK) >> SHIFT

4 // Form the address of the page-table entry (PTE)

5 PTEAddr = PTBR + (VPN * sizeof(PTE))

7 // Fetch the PTE

8 PTE = AccessMemory(PTEAddr)

10 // Check if process can access the page

11 if (PTE.Valid == False)

12 RaiseException(SEGMENTATION_FAULT)

13 else if (CanAccess(PTE.ProtectBits) == False)

14 RaiseException(PROTECTION_FAULT)

15 else

16 // Access OK: form physical address and fetch it

17 offset = VirtualAddress & OFFSET_MASK

18 PhysAddr = (PTE.PFN << PFN_SHIFT) | offset

19 Register = AccessMemory(PhysAddr)

Figure 18.6: Accessing Memory With Paging

work! Extra memory references are costly, and in this case will likely slow down the process by a factor of two or more.

And now you can hopefully see that there are two real problems that we must solve. Without careful design of both hardware and software, page tables will cause the system to run too slowly, as well as take up too much memory. While seemingly a great solution for our memory virtualization needs, these two crucial problems must ﬁrst be overcome.

18.5 A Memory Trace

Before closing, we now trace through a simple memory access example to demonstrate all of the resulting memory accesses that occur when using paging. The code snippet (in C, in a ﬁle called array.c) that we are interested in is as follows:

int array[1000]; ... for (i = 0; i < 1000; i++)

array[i] = 0;

We compile array.c and run it with the following commands:

prompt> gcc -o array array.c -Wall -O prompt> ./array

EASY PIECES

Of course, to truly understand what memory accesses this code snippet (which simply initializes an array) will make, we’ll have to know (or assume) a few more things. First, we’ll have to disassemble the resulting binary (using objdump on Linux, or otool on a Mac) to see what assembly instructions are used to initialize the array in a loop. Here is the resulting assembly code:

1024 movl $0x0,(%edi,%eax,4) 1028 incl %eax 1032 cmpl $0x03e8,%eax 1036 jne 1024

The code, if you know a little x86, is actually quite easy to understand2. The ﬁrst instruction moves the value zero (shown as $0x0) into the virtual memory address of the location of the array; this address is computed by taking the contents of %edi and adding %eax multiplied by four to it. Thus, %edi holds the base address of the array, whereas %eax holds the array index (i); we multiply by four because the array is an array of integers, each of size four bytes.

The second instruction increments the array index held in %eax, and the third instruction compares the contents of that register to the hex value 0x03e8, or decimal 1000. If the comparison shows that two values are not yet equal (which is what the jne instruction tests), the fourth instruction jumps back to the top of the loop.

To understand which memory accesses this instruction sequence makes (at both the virtual and physical levels), we’ll have to assume something about where in virtual memory the code snippet and array are found, as well as the contents and location of the page table.

For this example, we assume a virtual address space of size 64KB (unrealistically small). We also assume a page size of 1KB.

All we need to know now are the contents of the page table, and its location in physical memory. Let’s assume we have a linear (array-based) page table and that it is located at physical address 1KB (1024).

As for its contents, there are just a few virtual pages we need to worry about having mapped for this example. First, there is the virtual page the code lives on. Because the page size is 1KB, virtual address 1024 resides on the second page of the virtual address space (VPN=1, as VPN=0 is the ﬁrst page). Let’s assume this virtual page maps to physical frame 4 (VPN 1 →PFN 4).

Next, there is the array itself. Its size is 4000 bytes (1000 integers), and we assume that it resides at virtual addresses 40000 through 44000 (not including the last byte). The virtual pages for this decimal range are VPN=39 ... VPN=42. Thus, we need mappings for these pages. Let’s assume these virtual-to-physical mappings for the example: (VPN 39 →PFN 7), (VPN 40 →PFN 8), (VPN 41 →PFN 9), (VPN 42 →PFN 10).

2We are cheating a little bit here, assuming each instruction is four bytes in size for simplicity; in actuality, x86 instructions are variable-sized.

0 10 20 30 40 50 1024

Memory Access

Code (VA)

Array (VA)

Page Table (PA)

Code (PA)

Array (PA)

mov

inc

cmp

jne

mov

PageTable[1]

PageTable[39]

Figure 18.7: A Virtual (And Physical) Memory Trace We are now ready to trace the memory references of the program. When it runs, each instruction fetch will generate two memory references: one to the page table to ﬁnd the physical frame that the instruction resides within, and one to the instruction itself to fetch it to the CPU for processing. In addition, there is one explicit memory reference in the form of the mov instruction; this adds another page table access ﬁrst (to translate the array virtual address to the correct physical one) and then the array access itself.

The entire process, for the ﬁrst ﬁve loop iterations, is depicted in Figure 18.7 (page 11). The bottom most graph shows the instruction memory references on the y-axis in black (with virtual addresses on the left, and the actual physical addresses on the right); the middle graph shows array accesses in dark gray (again with virtual on left and physical on right); ﬁnally, the topmost graph shows page table memory accesses in light gray (just physical, as the page table in this example resides in physical memory). The x-axis, for the entire trace, shows memory accesses across the ﬁrst ﬁve iterations of the loop; there are 10 memory accesses per loop, which includes four instruction fetches, one explicit update of memory, and ﬁve page table accesses to translate those four fetches and one explicit update.

EASY PIECES

See if you can make sense of the patterns that show up in this visualization. In particular, what will change as the loop continues to run beyond these ﬁrst ﬁve iterations? Which new memory locations will be accessed? Can you ﬁgure it out?

This has just been the simplest of examples (only a few lines of C code), and yet you might already be able to sense the complexity of understanding the actual memory behavior of real applications. Don’t worry: it deﬁnitely gets worse, because the mechanisms we are about to introduce only complicate this already complex machinery. Sorry3!

18.6 Summary

We have introduced the concept of paging as a solution to our challenge of virtualizing memory. Paging has many advantages over previous approaches (such as segmentation). First, it does not lead to external fragmentation, as paging (by design) divides memory into ﬁxed-sized units. Second, it is quite ﬂexible, enabling the sparse use of virtual address spaces.

However, implementing paging support without care will lead to a slower machine (with many extra memory accesses to access the page table) as well as memory waste (with memory ﬁlled with page tables instead of useful application data). We’ll thus have to think a little harder to come up with a paging system that not only works, but works well. The next two chapters, fortunately, will show us how to do so.

3We’re not really sorry. But, we are sorry about not being sorry, if that makes sense.
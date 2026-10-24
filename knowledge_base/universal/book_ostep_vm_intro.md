# The Abstraction: Address Spaces (Operating Systems: Three Easy Pieces)

Source URL: https://pages.cs.wisc.edu/~remzi/OSTEP/vm-intro.pdf
Source: The Abstraction: Address Spaces (Operating Systems: Three Easy Pieces)
Licence: Free online textbook by the authors; downloaded for personal study, not redistributed
Retrieved: 2026-10-23

The Abstraction: Address Spaces

In the early days, building computer systems was easy. Why, you ask? Because users didn’t expect much. It is those darned users with their expectations of “ease of use”, “high performance”, “reliability”, etc., that really have led to all these headaches. Next time you meet one of those computer users, thank them for all the problems they have caused.

13.1 Early Systems

From the perspective of memory, early machines didn’t provide much of an abstraction to users. Basically, the physical memory of the machine looked something like what you see in Figure 13.1 (page 2).

The OS was a set of routines (a library, really) that sat in memory (starting at physical address 0 in this example), and there would be one running program (a process) that currently sat in physical memory (starting at physical address 64k in this example) and used the rest of memory. There were few illusions here, and the user didn’t expect much from the OS. Life was sure easy for OS developers in those days, wasn’t it?

13.2 Multiprogramming and Time Sharing

After a time, because machines were expensive, people began to share machines more effectively. Thus the era of multiprogramming was born [DV66], in which multiple processes were ready to run at a given time, and the OS would switch between them, for example when one decided to perform an I/O. Doing so increased the effective utilization of the CPU. Such increases in efﬁciency were particularly important in those days where each machine cost hundreds of thousands or even millions of dollars (and you thought your Mac was expensive!).

Soon enough, however, people began demanding more of machines, and the era of time sharing was born [S59, L60, M62, M83]. Speciﬁcally, many realized the limitations of batch computing, particularly on programmers themselves [CV65], who were tired of long (and hence ineffec-

max

64KB

0KB

Current Program (code, data, etc.)

Operating System

(code, data, etc.)

Figure 13.1: Operating Systems: The Early Days

tive) program-debug cycles. The notion of interactivity became important, as many users might be concurrently using a machine, each waiting for (or hoping for) a timely response from their currently-executing tasks.

One way to implement time sharing would be to run one process for a short while, giving it full access to all memory (Figure 13.1), then stop it, save all of its state to some kind of disk (including all of physical memory), load some other process’s state, run it for a while, and thus implement some kind of crude sharing of the machine [M+63].

Unfortunately, this approach has a big problem: it is way too slow, particularly as memory grows. While saving and restoring register-level state (the PC, general-purpose registers, etc.) is relatively fast, saving the entire contents of memory to disk is brutally non-performant. Thus, what we’d rather do is leave processes in memory while switching between them, allowing the OS to implement time sharing efﬁciently (as shown in Figure 13.2, page 3).

In the diagram, there are three processes (A, B, and C) and each of them have a small part of the 512KB physical memory carved out for them. Assuming a single CPU, the OS chooses to run one of the processes (say A), while the others (B and C) sit in the ready queue waiting to run.

As time sharing became more popular, you can probably guess that new demands were placed on the operating system. In particular, allowing multiple programs to reside concurrently in memory makes protection an important issue; you don’t want a process to be able to read, or worse, write some other process’s memory.

512KB

448KB

384KB

320KB

256KB

192KB

128KB

64KB

0KB

(free)

(free)

(free)

(free)

Operating System

(code, data, etc.)

Process A (code, data, etc.)

Process B (code, data, etc.)

Process C (code, data, etc.)

Figure 13.2: Three Processes: Sharing Memory

13.3 The Address Space

However, we have to keep those pesky users in mind, and doing so requires the OS to create an easy to use abstraction of physical memory. We call this abstraction the address space, and it is the running program’s view of memory in the system. Understanding this fundamental OS abstraction of memory is key to understanding how memory is virtualized.

The address space of a process contains all of the memory state of the running program. For example, the code of the program (the instructions) have to live in memory somewhere, and thus they are in the address space. The program, while it is running, uses a stack to keep track of where it is in the function call chain as well as to allocate local variables and pass parameters and return values to and from routines. Finally, the heap is used for dynamically-allocated, user-managed memory, such as that you might receive from a call to malloc() in C or new in an objectoriented language such as C++ or Java. Of course, there are other things in there too (e.g., statically-initialized variables), but for now let us just assume those three components: code, stack, and heap.

In the example in Figure 13.3 (page 4), we have a tiny address space (only 16KB)1. The program code lives at the top of the address space

1We will often use small examples like this because (a) it is a pain to represent a 32-bit address space and (b) the math is harder. We like simple math.

EASY PIECES

16KB

15KB

2KB

1KB

0KB

Stack

(free)

Heap

Program Code the code segment: where instructions live

the heap segment: contains malloc’d data dynamic data structures

(it grows positively)

(it grows negatively)

the stack segment: contains local variables arguments to routines,

return values, etc.

Figure 13.3: An Example Address Space

(starting at 0 in this example, and is packed into the ﬁrst 1K of the address space). Code is static (and thus easy to place in memory), so we can place it at the top of the address space and know that it won’t need any more space as the program runs.

Next, we have the two regions of the address space that may grow (and shrink) while the program runs. Those are the heap (at the top) and the stack (at the bottom). We place them like this because each wishes to be able to grow, and by putting them at opposite ends of the address space, we can allow such growth: they just have to grow in opposite directions. The heap thus starts just after the code (at 1KB) and grows downward (say when a user requests more memory via malloc()); the stack starts at 16KB and grows upward (say when a user makes a procedure call). However, this placement of stack and heap is just a convention; you could arrange the address space in a different way if you’d like (as we’ll see later, when multiple threads co-exist in an address space, no nice way to divide the address space like this works anymore, alas).

Of course, when we describe the address space, what we are describing is the abstraction that the OS is providing to the running program. The program really isn’t in memory at physical addresses 0 through 16KB; rather it is loaded at some arbitrary physical address(es). Examine processes A, B, and C in Figure 13.2; there you can see how each process is loaded into memory at a different address. And hence the problem:

THE CRUX: HOW TO VIRTUALIZE MEMORY How can the OS build this abstraction of a private, potentially large address space for multiple running processes (all sharing memory) on top of a single, physical memory?

When the OS does this, we say the OS is virtualizing memory, because the running program thinks it is loaded into memory at a particular address (say 0) and has a potentially very large address space (say 32-bits or 64-bits); the reality is quite different. When, for example, process A in Figure 13.2 tries to perform a load at address 0 (which we will call a virtual address), somehow the OS, in tandem with some hardware support, will have to make sure the load doesn’t actually go to physical address 0 but rather to physical address 320KB (where A is loaded into memory). This is the key to virtualization of memory, which underlies every modern computer system in the world.

13.4 Goals

Thus we arrive at the job of the OS in this set of notes: to virtualize memory. The OS will not only virtualize memory, though; it will do so with style. To make sure the OS does so, we need some goals to guide us. We have seen these goals before (think of the Introduction), and we’ll see them again, but they are certainly worth repeating.

One major goal of a virtual memory (VM) system is transparency2. The OS should implement virtual memory in a way that is invisible to the running program. Thus, the program shouldn’t be aware of the fact that memory is virtualized; rather, the program behaves as if it has its own private physical memory. Behind the scenes, the OS (and hardware) does all the work to multiplex memory among many different jobs, and hence implements the illusion.

Another goal of VM is efﬁciency. The OS should strive to make the virtualization as efﬁcient as possible, both in terms of time (i.e., not making programs run much more slowly) and space (i.e., not using too much memory for structures needed to support virtualization). In implementing time-efﬁcient virtualization, the OS will have to rely on hardware support, including hardware features such as TLBs (which we will learn about in due course).

Finally, a third VM goal is protection. The OS should make sure to protect processes from one another as well as the OS itself from pro-

2This usage of transparency is sometimes confusing; some students think that “being transparent” means keeping everything out in the open, i.e., what government should be like. Here, it means the opposite: that the illusion provided by the OS should not be visible to applications. Thus, in common usage, a transparent system is one that is hard to notice, not one that responds to requests as stipulated by the Freedom of Information Act.

EASY PIECES

TIP: THE PRINCIPLE OF ISOLATION Isolation is a key principle in building reliable systems. If two entities are properly isolated from one another, this implies that one can fail without affecting the other. Operating systems strive to isolate processes from each other and in this way prevent one from harming the other. By using memory isolation, the OS further ensures that running programs cannot affect the operation of the underlying OS. Some modern OS’s take isolation even further, by walling off pieces of the OS from other pieces of the OS. Such microkernels [BH70, R+89, S+03] thus may provide greater reliability than typical monolithic kernel designs.

cesses. When one process performs a load, a store, or an instruction fetch, it should not be able to access or affect in any way the memory contents of any other process or the OS itself (that is, anything outside its address space). Protection thus enables us to deliver the property of isolation among processes; each process should be running in its own isolated cocoon, safe from the ravages of other faulty or even malicious processes.

In the next chapters, we’ll focus our exploration on the basic mechanisms needed to virtualize memory, including hardware and operating systems support. We’ll also investigate some of the more relevant policies that you’ll encounter in operating systems, including how to manage free space and which pages to kick out of memory when you run low on space. In doing so, we’ll build up your understanding of how a modern virtual memory system really works3.

13.5 Summary

We have seen the introduction of a major OS subsystem: virtual memory. The VM system is responsible for providing the illusion of a large, sparse, private address space to each running program; each virtual address space contains all of a program’s instructions and data, which can be referenced by the program via virtual addresses. The OS, with some serious hardware help, will take each of these virtual memory references and turn them into physical addresses, which can be presented to the physical memory in order to fetch or update the desired information. The OS will provide this service for many processes at once, making sure to protect programs from one another, as well as protect the OS. The entire approach requires a great deal of mechanism (i.e., lots of low-level machinery) as well as some critical policies to work; we’ll start from the bottom up, describing the critical mechanisms ﬁrst. And thus we proceed!

3Or, we’ll convince you to drop the course. But hold on; if you make it through VM, you’ll likely make it all the way!

ASIDE: EVERY ADDRESS YOU SEE IS VIRTUAL Ever write a C program that prints out a pointer? The value you see (some large number, often printed in hexadecimal), is a virtual address. Ever wonder where the code of your program is found? You can print that out too, and yes, if you can print it, it also is a virtual address. In fact, any address you can see as a programmer of a user-level program is a virtual address. It’s only the OS, through its tricky techniques of virtualizing memory, that knows where in the physical memory of the machine these instructions and data values lie. So never forget: if you print out an address in a program, it’s a virtual one, an illusion of how things are laid out in memory; only the OS (and the hardware) knows the real truth. Here’s a little program (va.c) that prints out the locations of the main() routine (where code lives), the value of a heap-allocated value returned from malloc(), and the location of an integer on the stack:

1 #include <stdio.h>

2 #include <stdlib.h>

3 int main(int argc, char *argv[]) {

4 printf("location of code : %p\n", main);

5 printf("location of heap : %p\n", malloc(100e6));

6 int x = 3;

7 printf("location of stack: %p\n", &x);

8 return x;

9 }

When run on a 64-bit Mac, we get the following output:

location of code : 0x1095afe50 location of heap : 0x1096008c0 location of stack: 0x7fff691aea64

From this, you can see that code comes ﬁrst in the address space, then the heap, and the stack is all the way at the other end of this large virtual space. All of these addresses are virtual, and will be translated by the OS and hardware in order to fetch values from their true physical locations.

.

EASY PIECES
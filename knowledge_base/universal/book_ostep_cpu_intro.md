# The Abstraction: The Process (Operating Systems: Three Easy Pieces)

Source URL: https://pages.cs.wisc.edu/~remzi/OSTEP/cpu-intro.pdf
Source: The Abstraction: The Process (Operating Systems: Three Easy Pieces)
Licence: Free online textbook by the authors; downloaded for personal study, not redistributed
Retrieved: 2026-10-23

The Abstraction: The Process

In this chapter, we discuss one of the most fundamental abstractions that the OS provides to users: the process. The deﬁnition of a process, informally, is quite simple: it is a running program [V+65,BH70]. The program itself is a lifeless thing: it just sits there on the disk, a bunch of instructions (and maybe some static data), waiting to spring into action. It is the operating system that takes these bytes and gets them running, transforming the program into something useful.

It turns out that one often wants to run more than one program at once; for example, consider your desktop or laptop where you might like to run a web browser, mail program, a game, a music player, and so forth. In fact, a typical system may be seemingly running tens or even hundreds of processes at the same time. Doing so makes the system easy to use, as one never need be concerned with whether a CPU is available; one simply runs programs. Hence our challenge:

THE CRUX OF THE PROBLEM: HOW TO PROVIDE THE ILLUSION OF MANY CPUS? Although there are only a few physical CPUs available, how can the OS provide the illusion of a nearly-endless supply of said CPUs?

The OS creates this illusion by virtualizing the CPU. By running one process, then stopping it and running another, and so forth, the OS can promote the illusion that many virtual CPUs exist when in fact there is only one physical CPU (or a few). This basic technique, known as time sharing of the CPU, allows users to run as many concurrent processes as they would like; the potential cost is performance, as each will run more slowly if the CPU(s) must be shared.

To implement virtualization of the CPU, and to implement it well, the OS will need both some low-level machinery and some high-level intelligence. We call the low-level machinery mechanisms; mechanisms are low-level methods or protocols that implement a needed piece of functionality. For example, we’ll learn later how to implement a context

TIP: USE TIME SHARING (AND SPACE SHARING) Time sharing is a basic technique used by an OS to share a resource. By allowing the resource to be used for a little while by one entity, and then a little while by another, and so forth, the resource in question (e.g., the CPU, or a network link) can be shared by many. The counterpart of time sharing is space sharing, where a resource is divided (in space) among those who wish to use it. For example, disk space is naturally a spaceshared resource; once a block is assigned to a ﬁle, it is normally not assigned to another ﬁle until the user deletes the original ﬁle.

switch, which gives the OS the ability to stop running one program and start running another on a given CPU; this time-sharing mechanism is employed by all modern OSes.

On top of these mechanisms resides some of the intelligence in the OS, in the form of policies. Policies are algorithms for making some kind of decision within the OS. For example, given a number of possible programs to run on a CPU, which program should the OS run? A scheduling policy in the OS will make this decision, likely using historical information (e.g., which program has run more over the last minute?), workload knowledge (e.g., what types of programs are run), and performance metrics (e.g., is the system optimizing for interactive performance, or throughput?) to make its decision.

4.1 The Abstraction: A Process

The abstraction provided by the OS of a running program is something we will call a process. As we said above, a process is simply a running program; at any instant in time, we can summarize a process by taking an inventory of the different pieces of the system it accesses or affects during the course of its execution.

To understand what constitutes a process, we thus have to understand its machine state: what a program can read or update when it is running. At any given time, what parts of the machine are important to the execution of this program?

One obvious component of machine state that comprises a process is its memory. Instructions lie in memory; the data that the running program reads and writes sits in memory as well. Thus the memory that the process can address (called its address space) is part of the process.

Also part of the process’s machine state are registers; many instructions explicitly read or update registers and thus clearly they are important to the execution of the process.

Note that there are some particularly special registers that form part of this machine state. For example, the program counter (PC) (sometimes called the instruction pointer or IP) tells us which instruction of the program will execute next; similarly a stack pointer and associated frame

TIP: SEPARATE POLICY AND MECHANISM In many operating systems, a common design paradigm is to separate high-level policies from their low-level mechanisms [L+75]. You can think of the mechanism as providing the answer to a how question about a system; for example, how does an operating system perform a context switch? The policy provides the answer to a which question; for example, which process should the operating system run right now? Separating the two allows one easily to change policies without having to rethink the mechanism and is thus a form of modularity, a general software design principle.

pointer are used to manage the stack for function parameters, local variables, and return addresses.

Finally, programs often access persistent storage devices too. Such I/O information might include a list of the ﬁles the process currently has open.

4.2 Process API

Though we defer discussion of a real process API until a subsequent chapter, here we ﬁrst give some idea of what must be included in any interface of an operating system. These APIs, in some form, are available on any modern operating system.

• Create: An operating system must include some method to create new processes. When you type a command into the shell, or double-click on an application icon, the OS is invoked to create a new process to run the program you have indicated. • Destroy: As there is an interface for process creation, systems also provide an interface to destroy processes forcefully. Of course, many processes will run and just exit by themselves when complete; when they don’t, however, the user may wish to kill them, and thus an interface to halt a runaway process is quite useful. • Wait: Sometimes it is useful to wait for a process to stop running; thus some kind of waiting interface is often provided. • Miscellaneous Control: Other than killing or waiting for a process, there are sometimes other controls that are possible. For example, most operating systems provide some kind of method to suspend a process (stop it from running for a while) and then resume it (continue it running). • Status: There are usually interfaces to get some status information about a process as well, such as how long it has run for, or what state it is in.

EASY PIECES

Memory CPU

Disk

code static data

heap

stack

Process

code static data

Program Loading: Takes on-disk program

and reads it into the address space of process

Figure 4.1: Loading: From Program To Process

4.3 Process Creation: A Little More Detail

One mystery that we should unmask a bit is how programs are transformed into processes. Speciﬁcally, how does the OS get a program up and running? How does process creation actually work?

The ﬁrst thing that the OS must do to run a program is to load its code and any static data (e.g., initialized variables) into memory, into the address space of the process. Programs initially reside on disk (or, in some modern systems, ﬂash-based SSDs) in some kind of executable format; thus, the process of loading a program and static data into memory requires the OS to read those bytes from disk and place them in memory somewhere (as shown in Figure 4.1).

In early (or simple) operating systems, the loading process is done eagerly, i.e., all at once before running the program; modern OSes perform the process lazily, i.e., by loading pieces of code or data only as they are needed during program execution. To truly understand how lazy loading of pieces of code and data works, you’ll have to understand more about

the machinery of paging and swapping, topics we’ll cover in the future when we discuss the virtualization of memory. For now, just remember that before running anything, the OS clearly must do some work to get the important program bits from disk into memory.

Once the code and static data are loaded into memory, there are a few other things the OS needs to do before running the process. Some memory must be allocated for the program’s run-time stack (or just stack). As you should likely already know, C programs use the stack for local variables, function parameters, and return addresses; the OS allocates this memory and gives it to the process. The OS will also likely initialize the stack with arguments; speciﬁcally, it will ﬁll in the parameters to the main() function, i.e., argc and the argv array.

The OS may also allocate some memory for the program’s heap. In C programs, the heap is used for explicitly requested dynamically-allocated data; programs request such space by calling malloc() and free it explicitly by calling free(). The heap is needed for data structures such as linked lists, hash tables, trees, and other interesting data structures. The heap will be small at ﬁrst; as the program runs, and requests more memory via the malloc() library API, the OS may get involved and allocate more memory to the process to help satisfy such calls.

The OS will also do some other initialization tasks, particularly as related to input/output (I/O). For example, in UNIX systems, each process by default has three open ﬁle descriptors, for standard input, output, and error; these descriptors let programs easily read input from the terminal and print output to the screen. We’ll learn more about I/O, ﬁle descriptors, and the like in the third part of the book on persistence.

By loading the code and static data into memory, by creating and initializing a stack, and by doing other work as related to I/O setup, the OS has now (ﬁnally) set the stage for program execution. It thus has one last task: to start the program running at the entry point, namely main(). By jumping to the main() routine (through a specialized mechanism that we will discuss next chapter), the OS transfers control of the CPU to the newly-created process, and thus the program begins its execution.

4.4 Process States

Now that we have some idea of what a process is (though we will continue to reﬁne this notion), and (roughly) how it is created, let us talk about the different states a process can be in at a given time. The notion that a process can be in one of these states arose in early computer systems [DV66,V+65]. In a simpliﬁed view, a process can be in one of three states:

• Running: In the running state, a process is running on a processor. This means it is executing instructions. • Ready: In the ready state, a process is ready to run but for some reason the OS has chosen not to run it at this given moment.

EASY PIECES

Running Ready

Blocked

Descheduled

Scheduled

I/O: initiate I/O: done

Figure 4.2: Process: State Transitions

• Blocked: In the blocked state, a process has performed some kind of operation that makes it not ready to run until some other event takes place. A common example: when a process initiates an I/O request to a disk, it becomes blocked and thus some other process can use the processor.

If we were to map these states to a graph, we would arrive at the diagram in Figure 4.2. As you can see in the diagram, a process can be moved between the ready and running states at the discretion of the OS. Being moved from ready to running means the process has been scheduled; being moved from running to ready means the process has been descheduled. Once a process has become blocked (e.g., by initiating an I/O operation), the OS will keep it as such until some event occurs (e.g., I/O completion); at that point, the process moves to the ready state again (and potentially immediately to running again, if the OS so decides).

Let’s look at an example of how two processes might transition through some of these states. First, imagine two processes running, each of which only use the CPU (they do no I/O). In this case, a trace of the state of each process might look like this (Figure 4.3).

Time Process0 Process1 Notes 1 Running Ready 2 Running Ready 3 Running Ready 4 Running Ready Process0 now done 5 – Running 6 – Running 7 – Running 8 – Running Process1 now done

Figure 4.3: Tracing Process State: CPU Only

Time Process0 Process1 Notes 1 Running Ready 2 Running Ready 3 Running Ready Process0 initiates I/O 4 Blocked Running Process0 is blocked, 5 Blocked Running so Process1 runs 6 Blocked Running 7 Ready Running I/O done 8 Ready Running Process1 now done 9 Running – 10 Running – Process0 now done

Figure 4.4: Tracing Process State: CPU and I/O

In this next example, the ﬁrst process issues an I/O after running for some time. At that point, the process is blocked, giving the other process a chance to run. Figure 4.4 shows a trace of this scenario.

More speciﬁcally, Process0 initiates an I/O and becomes blocked waiting for it to complete; processes become blocked, for example, when reading from a disk or waiting for a packet from a network. The OS recognizes Process0 is not using the CPU and starts running Process1. While Process1 is running, the I/O completes, moving Process0 back to ready. Finally, Process1 ﬁnishes, and Process0 runs and then is done.

Note that there are many decisions the OS must make, even in this simple example. First, the system had to decide to run Process1 while Process0 issued an I/O; doing so improves resource utilization by keeping the CPU busy. Second, the system decided not to switch back to Process0 when its I/O completed; it is not clear if this is a good decision or not. What do you think? These types of decisions are made by the OS scheduler, a topic we will discuss a few chapters in the future.

4.5 Data Structures

The OS is a program, and like any program, it has some key data structures that track various relevant pieces of information. To track the state of each process, for example, the OS likely will keep some kind of process list for all processes that are ready and some additional information to track which process is currently running. The OS must also track, in some way, blocked processes; when an I/O event completes, the OS should make sure to wake the correct process and ready it to run again.

Figure 4.5 shows what type of information an OS needs to track about each process in the xv6 kernel [CK+08]. Similar process structures exist in “real” operating systems such as Linux, Mac OS X, or Windows; look them up and see how much more complex they are.

From the ﬁgure, you can see a couple of important pieces of information the OS tracks about a process. The register context will hold, for a

EASY PIECES

// the registers xv6 will save and restore // to stop and subsequently restart a process struct context {

int eip; int esp; int ebx; int ecx; int edx; int esi; int edi; int ebp; };

// the different states a process can be in enum proc_state { UNUSED, EMBRYO, SLEEPING,

RUNNABLE, RUNNING, ZOMBIE };

// the information xv6 tracks about each process // including its register context and state struct proc {

char *mem; // Start of process memory uint sz; // Size of process memory char *kstack; // Bottom of kernel stack // for this process enum proc_state state; // Process state int pid; // Process ID struct proc *parent; // Parent process void *chan; // If !zero, sleeping on chan int killed; // If !zero, has been killed struct file *ofile[NOFILE]; // Open files struct inode *cwd; // Current directory struct context context; // Switch here to run process struct trapframe *tf; // Trap frame for the // current interrupt };

Figure 4.5: The xv6 Proc Structure

stopped process, the contents of its registers. When a process is stopped, its registers will be saved to this memory location; by restoring these registers (i.e., placing their values back into the actual physical registers), the OS can resume running the process. We’ll learn more about this technique known as a context switch in future chapters.

You can also see from the ﬁgure that there are some other states a process can be in, beyond running, ready, and blocked. Sometimes a system will have an initial state that the process is in when it is being created. Also, a process could be placed in a ﬁnal state where it has exited but

ASIDE: DATA STRUCTURE — THE PROCESS LIST Operating systems are replete with various important data structures that we will discuss in these notes. The process list (also called the task list) is the ﬁrst such structure. It is one of the simpler ones, but certainly any OS that has the ability to run multiple programs at once will have something akin to this structure in order to keep track of all the running programs in the system. Sometimes people refer to the individual structure that stores information about a process as a Process Control Block (PCB), a fancy way of talking about a C structure that contains information about each process (also sometimes called a process descriptor).

has not yet been cleaned up (in UNIX-based systems, this is called the zombie state1). This ﬁnal state can be useful as it allows other processes (usually the parent that created the process) to examine the return code of the process and see if the just-ﬁnished process executed successfully (usually, programs return zero in UNIX-based systems when they have accomplished a task successfully, and non-zero otherwise). When ﬁnished, the parent will make one ﬁnal call (e.g., wait()) to wait for the completion of the child, and to also indicate to the OS that it can clean up any relevant data structures that referred to the now-extinct process.

4.6 Summary

We have introduced the most basic abstraction of the OS: the process. It is quite simply viewed as a running program. With this conceptual view in mind, we will now move on to the nitty-gritty: the low-level mechanisms needed to implement processes, and the higher-level policies required to schedule them in an intelligent way. By combining mechanisms and policies, we will build up our understanding of how an operating system virtualizes the CPU.

1Yes, the zombie state. Just like real zombies, these zombies are relatively easy to kill. However, different techniques are usually recommended.

EASY PIECES

ASIDE: KEY PROCESS TERMS • The process is the major OS abstraction of a running program. At any point in time, the process can be described by its state: the contents of memory in its address space, the contents of CPU registers (including the program counter and stack pointer, among others), and information about I/O (such as open ﬁles which can be read or written).

• The process API consists of calls programs can make related to processes. Typically, this includes creation, destruction, and other useful calls.

• Processes exist in one of many different process states, including running, ready to run, and blocked. Different events (e.g., getting scheduled or descheduled, or waiting for an I/O to complete) transition a process from one of these states to the other.

• A process list contains information about all processes in the system. Each entry is found in what is sometimes called a process control block (PCB), which is really just a structure that contains information about a speciﬁc process.
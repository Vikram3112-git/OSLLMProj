# Introduction, OS Structure, System Calls and Interrupts

## What an operating system is
An operating system (OS) is the program that manages the computer's hardware and provides services to application programs. Two standard views:
- Resource allocator: it decides how the CPU, memory, storage and devices are shared between programs and users, fairly and efficiently.
- Control program: it supervises programs so that errors and misuse do not harm the system.

Goals of an operating system: convenience for the user, efficient use of the hardware, and the ability to evolve (new hardware and services can be added without rewriting everything).

A computer system has four components: the hardware (CPU, memory, I/O devices), the operating system, application programs, and users.

## Kernel and shell
- The kernel is the core of the OS. It is the one program that runs at all times; it manages processes, memory, files and devices.
- The shell is a user program that reads commands and asks the kernel to carry them out (bash and zsh on Linux). It is the user's interface to the kernel; it is not part of the kernel.

## Dual-mode operation
The CPU has a mode bit: kernel mode (0) and user mode (1). Privileged instructions (I/O, changing the timer, managing interrupts, changing memory protection) can only run in kernel mode. User programs run in user mode; when they need a service, they make a system call, which switches the CPU to kernel mode, runs the kernel code, and switches back. A timer interrupt makes sure the OS regains control even from a program stuck in a loop.

## Operating system structures
- Monolithic: the whole kernel is one large program in one address space (traditional UNIX; Linux). Fast, because calls between parts are ordinary function calls, but a bug anywhere can crash the system and it is hard to maintain.
- Layered: the OS is split into layers; each layer uses only the services of the layers below it. Easy to debug, but hard to define the layers and slower because a request passes through many layers.
- Microkernel: only the essentials (inter-process communication, basic scheduling, low-level memory management) stay in the kernel; file systems, drivers and so on run as user-space servers that communicate by message passing (Mach, QNX). More reliable and secure, but message passing adds overhead.
- Modular: a core kernel plus loadable kernel modules that can be added at run time (Linux modules, Solaris). Combines the speed of monolithic kernels with flexibility.
- Hybrid: a mix of the above (Windows; macOS and iOS with the XNU kernel, which combines Mach with BSD code).

## Key abstractions
The OS hides hardware details behind abstractions: the process (a running program), virtual memory (each process sees its own large address space), the file (named persistent data), devices (uniform interfaces to hardware), and threads (units of execution inside a process).

## System calls
A system call is the programming interface to the services of the OS: a controlled way for a user program to ask the kernel to do something it is not allowed to do itself.

Life cycle of a system call:
1. The program calls a library wrapper function, for example `read()` in the C library.
2. The wrapper puts the system-call number and the parameters in agreed places and executes a trap instruction.
3. The trap switches the CPU to kernel mode and jumps to the system-call handler.
4. The handler looks the number up in the system-call table and runs the matching kernel function.
5. The result is placed in a register, the CPU returns to user mode, and the wrapper returns the value.

Parameter passing: in registers (fastest, but limited), in a block or table in memory whose address is passed in a register (used by Linux for many parameters), or pushed on the stack.

Types of system calls with examples:
- Process control: fork(), exec(), exit(), wait(), kill()
- File management: open(), read(), write(), close(), lseek()
- Device management: ioctl(), read(), write() on device files
- Information maintenance: getpid(), time(), alarm(), sleep()
- Communication: pipe(), shmget(), mmap(), socket(), send(), recv()
- Protection: chmod(), chown(), umask()

System call vs function call: a function call stays in user mode and in the program's own address space; a system call crosses into the kernel through a trap, changes the mode, and is much more expensive.

## Interrupts
An interrupt is a signal that makes the CPU stop what it is doing and run an interrupt service routine (ISR).
- Hardware interrupts come from devices (a disk finishing a transfer, a key press, the timer).
- Software interrupts (traps or exceptions) come from the running program: an error such as division by zero or an invalid memory access, or a deliberate system call.

Interrupt handling: the CPU finishes the current instruction, saves the program counter and state, looks up the handler address in the interrupt vector (a table of ISR addresses indexed by interrupt number), runs the ISR, then restores the state and continues. Interrupts can be masked (disabled for a short time) and have priorities.

I/O methods: polling (the CPU keeps checking the device: simple but wastes CPU time), interrupt-driven I/O (the device interrupts when ready), and DMA (direct memory access: a controller moves a whole block between device and memory and interrupts once at the end, used for fast devices).

## Common mistakes
- Saying the shell is part of the kernel. It is a user program.
- Confusing a trap (raised by the running program) with a hardware interrupt (raised by a device).
- Thinking a system call is just a library function. The library function only wraps the trap.

## Viva questions
- Why do we need dual-mode operation? To protect the OS and other programs: only the kernel can run privileged instructions.
- What happens when a program calls read()? The wrapper traps into the kernel with the system-call number; the kernel runs sys_read and returns the result.
- Which structure does Linux use? Monolithic with loadable kernel modules.
- Why is a microkernel more reliable? A failing driver or file server runs in user space and can be restarted without crashing the kernel.

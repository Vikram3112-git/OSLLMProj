# Virtual Memory: Demand Paging, Page Replacement, Thrashing

## Virtual memory
Virtual memory separates the logical memory of a process from physical memory. Only the parts of a program that are needed are in memory, so programs can be larger than physical memory, more programs can run at once, and less I/O is needed to load or swap.

## Demand paging
Pages are loaded only when they are first used (lazy loading). Each page-table entry has a valid-invalid bit: valid means the page is in memory; invalid means it is not in memory (or not part of the address space). Pure demand paging starts a process with no pages in memory.

Page-fault handling:
1. The process references a page whose entry is invalid, and the hardware traps to the OS (page fault).
2. The OS checks an internal table: if the reference is not valid, the process is terminated; if it is valid but not in memory, the page must be brought in.
3. Find a free frame (or choose a victim with a page-replacement algorithm).
4. Schedule a disk read of the page into the frame.
5. When the read finishes, update the page table (valid) and the internal table.
6. Restart the instruction that caused the fault.

Effective access time with page faults: EAT = (1 − p) × memory access time + p × page-fault service time, where p is the page-fault rate.
Example: memory access 200 ns, fault service time 8 ms = 8,000,000 ns. With p = 1/1000: EAT = 0.999 × 200 + 0.001 × 8,000,000 = 199.8 + 8000 = 8199.8 ns, about 8.2 microseconds, a slowdown of about 40 times. To keep the slowdown under 10% (EAT < 220 ns) we need 220 > 200 + 7,999,800 × p, so p < 0.0000025: fewer than one fault in about 400,000 accesses.

Copy-on-write: after fork(), parent and child share pages marked copy-on-write; a page is copied only when one of them writes to it.

## Page replacement
When a page fault occurs and no frame is free, the OS chooses a victim frame, writes it to disk if it has been modified (dirty bit set), reads in the new page and restarts the process. Algorithms are compared by the number of page faults on a reference string.

- FIFO: replace the page that has been in memory the longest. Simple, but it can replace heavily used pages, and it suffers from Belady's anomaly.
- Optimal (OPT): replace the page that will not be used for the longest time in the future. It gives the lowest possible number of faults, but needs future knowledge, so it is used as a benchmark. (Course convention: among pages never used again, the one loaded earliest is replaced.)
- LRU (least recently used): replace the page that has not been used for the longest time. A good approximation of OPT; implemented with counters (time of last use) or a stack of page numbers, or approximated in hardware.

## Worked example (solved exactly by OSLLM's solver)
Reference string 7 0 1 2 0 3 0 4 2 3 0 3 2 1 2 0 1 7 0 1 with 3 frames:
- FIFO: 15 page faults, 5 hits. Frames after each reference: 7-- | 70- | 701 | 201 | 201 | 231 | 230 | 430 | 420 | 423 | 023 | 023 | 023 | 013 | 012 | 012 | 012 | 712 | 702 | 701.
- LRU: 12 page faults, 8 hits. Frames: 7-- | 70- | 701 | 201 | 201 | 203 | 203 | 403 | 402 | 432 | 032 | 032 | 032 | 132 | 132 | 102 | 102 | 107 | 107 | 107.
- OPT: 9 page faults, 11 hits. Frames: 7-- | 70- | 701 | 201 | 201 | 203 | 203 | 243 | 243 | 243 | 203 | 203 | 203 | 201 | 201 | 201 | 201 | 701 | 701 | 701.
Hit ratio = hits ÷ references; for LRU 8/20 = 40%.

## Belady's anomaly
With FIFO, adding frames can increase the number of page faults. Reference string 1 2 3 4 1 2 5 1 2 3 4 5: FIFO gives 9 faults with 3 frames but 10 faults with 4 frames. LRU and OPT are stack algorithms (the pages in memory with n frames are always a subset of those with n + 1 frames), so they never show Belady's anomaly.

## LRU approximations
- Reference bit: set by hardware when a page is used; the OS clears it periodically.
- Second-chance (clock) algorithm: FIFO order in a circular list; if the victim's reference bit is 1, clear it, give the page a second chance and move on; replace the first page found with reference bit 0.
- Counting algorithms: LFU (least frequently used) and MFU (most frequently used); not common.

## Frame allocation
- Equal allocation: m frames among n processes, m/n each.
- Proportional allocation: a_i = (s_i / S) × m, where s_i is the size of process i and S the total. Example: 62 frames, processes of 10 and 127 pages: 10/137 × 62 ≈ 4 frames and 127/137 × 62 ≈ 57 frames.
- Global replacement: a process may take a frame from any process (better throughput, but a process cannot control its own fault rate). Local replacement: only from its own frames.

## Thrashing
A process is thrashing when it spends more time paging than executing. Cause: the processes do not have enough frames for the pages they are actively using, so they fault constantly. The OS sees low CPU utilisation, adds more processes, which makes it worse; CPU utilisation collapses as the degree of multiprogramming rises.

Locality model: a process moves from one locality (a set of pages used together) to another. Thrashing happens when the total size of the current localities is larger than memory.

Working-set model: the working set WS(t, Δ) is the set of pages referenced in the last Δ references (the working-set window). Let D = Σ WSS_i be the total demand. If D > m (available frames), thrashing will occur, so the OS suspends a process. Example: with Δ = 10 and the last ten references 1 2 1 5 7 7 7 7 5 1, the working set is {1, 2, 5, 7}, so WSS = 4.

Page-fault frequency (PFF): set an upper and a lower bound on the fault rate; if a process faults too often, give it more frames; if too rarely, take frames away.

## Common mistakes
- In OPT, looking backwards instead of forwards in the reference string.
- In LRU, using the time a page was loaded instead of the time it was last used (that would be FIFO).
- Counting the first loads into empty frames as hits. They are page faults.
- Thinking more frames always means fewer faults. Not for FIFO (Belady's anomaly).

## Viva questions
- Why is OPT not used in practice? It needs to know the future reference string.
- What causes thrashing and how is it controlled? Too few frames for the active localities; control it with the working-set model or page-fault frequency and by reducing multiprogramming.
- What is the dirty bit for? To avoid writing a page back to disk if it was not modified.

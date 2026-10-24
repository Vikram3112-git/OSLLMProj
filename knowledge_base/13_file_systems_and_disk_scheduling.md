# File Systems and Disk Scheduling

## File concept
A file is a named collection of related information stored on secondary storage. Attributes: name, identifier, type, location, size, protection, timestamps and owner. Operations: create, open, read, write, reposition (seek), delete, truncate, close. The OS keeps an open-file table with the file pointer, open count, location and access rights.

## Access methods
- Sequential access: records are read in order (like a tape); read_next and write_next.
- Direct (relative) access: any block can be read or written by number; used by databases.
- Indexed access: an index file holds pointers to blocks; search the index, then go directly to the block.

## Directory structures
- Single-level: one directory for all users; name clashes.
- Two-level: a separate directory for each user.
- Tree-structured: directories inside directories; absolute and relative path names.
- Acyclic graph: files and subdirectories can be shared through links; deletion needs care (dangling pointers, reference counts).
- General graph: allows cycles; needs garbage collection.

## Allocation methods
- Contiguous: each file occupies consecutive blocks; the directory stores the start and length. Supports sequential and direct access and is fast, but suffers external fragmentation and files are hard to grow.
- Linked: each block points to the next; the directory stores the first and last block. No external fragmentation and files grow easily, but direct access is slow and a damaged pointer loses the rest of the file. FAT (file-allocation table) keeps all the links in one table at the start of the disk.
- Indexed: each file has an index block holding the addresses of all its blocks (UNIX inode). Supports direct access without external fragmentation; costs an index block per file. Large files use linked index blocks or multilevel indexes.

UNIX inode: 12 direct block pointers, one single indirect, one double indirect and one triple indirect pointer. With 4 KB blocks and 4-byte pointers, one block holds 1024 pointers, so the maximum file size is 12 × 4 KB + 1024 × 4 KB + 1024² × 4 KB + 1024³ × 4 KB = 48 KB + 4 MB + 4 GB + 4 TB, about 4 TB.

Hard link vs soft link: a hard link is another directory entry pointing to the same inode (the file is deleted only when the link count reaches 0; cannot cross file systems). A soft (symbolic) link is a separate small file holding a path name; it breaks if the target is deleted.

## Free-space management
- Bit vector (bitmap): one bit per block (1 = free). Easy to find contiguous free blocks; for a 1 TB disk with 4 KB blocks it needs 2^28 bits = 32 MB.
- Linked list: free blocks linked together; no wasted space but slow to traverse.
- Grouping: the first free block stores the addresses of n free blocks.
- Counting: store the address of the first free block and the number of free blocks that follow it.

## Disk structure and access time
A hard disk has platters with tracks; the tracks at one arm position form a cylinder; tracks are divided into sectors. Access time = seek time (moving the head to the cylinder) + rotational latency (waiting for the sector to come under the head) + transfer time. Seek time is the largest part, and disk scheduling tries to reduce the total head movement.

## Disk scheduling algorithms
Course conventions: SSTF ties go to the request that comes first in the queue; SCAN and C-SCAN travel to the edge of the disk; the return jump of C-SCAN and C-LOOK is counted in the total head movement.
- FCFS: serve requests in arrival order. Fair, but can swing the head wildly.
- SSTF (shortest seek time first): always serve the closest pending request. Much less movement, but requests far from the head can starve; it is not always optimal.
- SCAN (elevator): move in one direction serving requests until the end of the disk, then reverse.
- C-SCAN (circular SCAN): move in one direction to the end, jump back to the other end, and continue in the same direction. Gives a more uniform waiting time.
- LOOK: like SCAN, but reverse at the last request in that direction instead of going to the edge.
- C-LOOK: like C-SCAN, but go only as far as the last request and jump back to the farthest request on the other side.

## Worked example (solved exactly by OSLLM's solver)
Request queue 98, 183, 37, 122, 14, 124, 65, 67; head at 53; cylinders 0 to 199.
- FCFS: 53 → 98 → 183 → 37 → 122 → 14 → 124 → 65 → 67, total head movement 640 cylinders.
- SSTF: 53 → 65 → 67 → 37 → 14 → 98 → 122 → 124 → 183, total 236.
- SCAN moving towards 0: 53 → 37 → 14 → 0 → 65 → 67 → 98 → 122 → 124 → 183, total 53 + 183 = 236.
- SCAN moving towards 199: 53 → 65 → ... → 183 → 199 → 37 → 14, total (199 − 53) + (199 − 14) = 331.
- C-SCAN moving towards 199: 53 → 65 → 67 → 98 → 122 → 124 → 183 → 199 → 0 → 14 → 37, total 146 + 199 + 37 = 382.
- LOOK moving towards 0: 53 → 37 → 14 → 65 → ... → 183, total 39 + 169 = 208. Towards 199: 53 → ... → 183 → 37 → 14, total 130 + 169 = 299.
- C-LOOK moving towards 199: 53 → 65 → 67 → 98 → 122 → 124 → 183 → 14 → 37, total 130 + 169 + 23 = 322.
Average seek distance = total ÷ number of requests; for SSTF 236/8 = 29.5 cylinders.

Choosing an algorithm: SSTF is common and simple; SCAN and C-SCAN perform better under heavy load and avoid starvation; with SSDs there is no seek, so FCFS (or a simple merging queue) is used.

## Common mistakes
- Forgetting the move to the edge of the disk in SCAN and C-SCAN.
- Leaving out (or adding, against the course convention) the return jump in C-SCAN and C-LOOK.
- Going the wrong way first; read the direction in the question.
- Saying SSTF is optimal. It is greedy and can starve far requests.

## Viva questions
- Difference between SCAN and LOOK? LOOK reverses at the last request; SCAN goes to the end of the disk.
- Why does C-SCAN give more uniform waiting times? It always serves in the same direction, so cylinders at both ends wait about the same time.
- Advantage of indexed allocation over linked? Direct access to any block without following pointers.

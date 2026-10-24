# File System Implementation (Operating Systems: Three Easy Pieces)

Source URL: https://pages.cs.wisc.edu/~remzi/OSTEP/file-implementation.pdf
Source: File System Implementation (Operating Systems: Three Easy Pieces)
Licence: Free online textbook by the authors; downloaded for personal study, not redistributed
Retrieved: 2026-10-23

File System Implementation

In this chapter, we introduce a simple ﬁle system implementation, known as vsfs (the Very Simple File System). This ﬁle system is a simpliﬁed version of a typical UNIX ﬁle system and thus serves to introduce some of the basic on-disk structures, access methods, and various policies that you will ﬁnd in many ﬁle systems today.

The ﬁle system is pure software; unlike our development of CPU and memory virtualization, we will not be adding hardware features to make some aspect of the ﬁle system work better (though we will want to pay attention to device characteristics to make sure the ﬁle system works well). Because of the great ﬂexibility we have in building a ﬁle system, many different ones have been built, literally from AFS (the Andrew File System) [H+88] to ZFS (Sun’s Zettabyte File System) [B07]. All of these ﬁle systems have different data structures and do some things better or worse than their peers. Thus, the way we will be learning about ﬁle systems is through case studies: ﬁrst, a simple ﬁle system (vsfs) in this chapter to introduce most concepts, and then a series of studies of real ﬁle systems to understand how they can differ in practice.

THE CRUX: HOW TO IMPLEMENT A SIMPLE FILE SYSTEM How can we build a simple ﬁle system? What structures are needed on the disk? What do they need to track? How are they accessed?

40.1 The Way To Think

To think about ﬁle systems, we usually suggest thinking about two different aspects of them; if you understand both of these aspects, you probably understand how the ﬁle system basically works.

The ﬁrst is the data structures of the ﬁle system. In other words, what types of on-disk structures are utilized by the ﬁle system to organize its data and metadata? The ﬁrst ﬁle systems we’ll see (including vsfs below) employ simple structures, like arrays of blocks or other objects, whereas

ASIDE: MENTAL MODELS OF FILE SYSTEMS As we’ve discussed before, mental models are what you are really trying to develop when learning about systems. For ﬁle systems, your mental model should eventually include answers to questions like: what on-disk structures store the ﬁle system’s data and metadata? What happens when a process opens a ﬁle? Which on-disk structures are accessed during a read or write? By working on and improving your mental model, you develop an abstract understanding of what is going on, instead of just trying to understand the speciﬁcs of some ﬁle-system code (though that is also useful, of course!).

more sophisticated ﬁle systems, like SGI’s XFS, use more complicated tree-based structures [S+96].

The second aspect of a ﬁle system is its access methods. How does it map the calls made by a process, such as open(), read(), write(), etc., onto its structures? Which structures are read during the execution of a particular system call? Which are written? How efﬁciently are all of these steps performed?

If you understand the data structures and access methods of a ﬁle system, you have developed a good mental model of how it truly works, a key part of the systems mindset. Try to work on developing your mental model as we delve into our ﬁrst implementation.

40.2 Overall Organization

We now develop the overall on-disk organization of the data structures of the vsfs ﬁle system. The ﬁrst thing we’ll need to do is divide the disk into blocks; simple ﬁle systems use just one block size, and that’s exactly what we’ll do here. Let’s choose a commonly-used size of 4 KB.

Thus, our view of the disk partition where we’re building our ﬁle system is simple: a series of blocks, each of size 4 KB. The blocks are addressed from 0 to N −1, in a partition of size N 4-KB blocks. Assume we have a really small disk, with just 64 blocks:

0 7 8 15 16 23 24 31

32 39 40 47 48 55 56 63

Let’s now think about what we need to store in these blocks to build a ﬁle system. Of course, the ﬁrst thing that comes to mind is user data. In fact, most of the space in any ﬁle system is (and should be) user data. Let’s call the region of the disk we use for user data the data region, and,

again for simplicity, reserve a ﬁxed portion of the disk for these blocks, say the last 56 of 64 blocks on the disk:

0 7 D

15 D 16 D D D D D D D

23 D 24 D D D D D D D

D 32 D D D D D D D

39 D 40 D D D D D D D

47 D 48 D D D D D D D

55 D 56 D D D D D D D

Data Region

Data Region

As we learned about (a little) last chapter, the ﬁle system has to track information about each ﬁle. This information is a key piece of metadata, and tracks things like which data blocks (in the data region) comprise a ﬁle, the size of the ﬁle, its owner and access rights, access and modify times, and other similar kinds of information. To store this information, ﬁle systems usually have a structure called an inode (we’ll read more about inodes below).

To accommodate inodes, we’ll need to reserve some space on the disk for them as well. Let’s call this portion of the disk the inode table, which simply holds an array of on-disk inodes. Thus, our on-disk image now looks like this picture, assuming that we use 5 of our 64 blocks for inodes (denoted by I’s in the diagram):

I I I I I 7 D

15 D 16 D D D D D D D

23 D 24 D D D D D D D

D 32 D D D D D D D

39 D 40 D D D D D D D

47 D 48 D D D D D D D

55 D 56 D D D D D D D

Data Region

Data Region

Inodes

We should note here that inodes are typically not that big, for example 128 or 256 bytes. Assuming 256 bytes per inode, a 4-KB block can hold 16 inodes, and our ﬁle system above contains 80 total inodes. In our simple ﬁle system, built on a tiny 64-block partition, this number represents the maximum number of ﬁles we can have in our ﬁle system; however, do note that the same ﬁle system, built on a larger disk, could simply allocate a larger inode table and thus accommodate more ﬁles.

Our ﬁle system thus far has data blocks (D), and inodes (I), but a few things are still missing. One primary component that is still needed, as you might have guessed, is some way to track whether inodes or data blocks are free or allocated. Such allocation structures are thus a requisite element in any ﬁle system.

Many allocation-tracking methods are possible, of course. For example, we could use a free list that points to the ﬁrst free block, which then points to the next free block, and so forth. We instead choose a simple and popular structure known as a bitmap, one for the data region (the data bitmap), and one for the inode table (the inode bitmap). A bitmap is a

EASY PIECES

simple structure: each bit is used to indicate whether the corresponding object/block is free (0) or in-use (1). And thus our new on-disk layout, with an inode bitmap (i) and a data bitmap (d):

0 i d I I I I I 7 D

15 D 16 D D D D D D D

23 D 24 D D D D D D D

D 32 D D D D D D D

39 D 40 D D D D D D D

47 D 48 D D D D D D D

55 D 56 D D D D D D D

Data Region

Data Region

Inodes

You may notice that it is a bit of overkill to use an entire 4-KB block for these bitmaps; such a bitmap can track whether 32K objects are allocated, and yet we only have 80 inodes and 56 data blocks. However, we just use an entire 4-KB block for each of these bitmaps for simplicity.

The careful reader (i.e., the reader who is still awake) may have noticed there is one block left in the design of the on-disk structure of our very simple ﬁle system. We reserve this for the superblock, denoted by an S in the diagram below. The superblock contains information about this particular ﬁle system, including, for example, how many inodes and data blocks are in the ﬁle system (80 and 56, respectively in this instance), where the inode table begins (block 3), and so forth. It will likely also include a magic number of some kind to identify the ﬁle system type (in this case, vsfs).

S 0 i d I I I I I 7 D

15 D 16 D D D D D D D

23 D 24 D D D D D D D

D 32 D D D D D D D

39 D 40 D D D D D D D

47 D 48 D D D D D D D

55 D 56 D D D D D D D

Data Region

Data Region

Inodes

Thus, when mounting a ﬁle system, the operating system will read the superblock ﬁrst, to initialize various parameters, and then attach the volume to the ﬁle-system tree. When ﬁles within the volume are accessed, the system will thus know exactly where to look for the needed on-disk structures.

40.3 File Organization: The Inode

One of the most important on-disk structures of a ﬁle system is the inode; virtually all ﬁle systems have a structure similar to this. The name inode is short for index node, the historical term used in UNIX [RT74] and possibly earlier systems. The name reﬂects the fact that these nodes were originally stored in an array, which the system indexed into to access a particular inode.

ASIDE: DATA STRUCTURE — THE INODE The inode is the generic name that is used in many ﬁle systems to describe the structure that holds the metadata for a given ﬁle, such as its length, permissions, and the location of its constituent blocks. The name goes back at least as far as UNIX (and probably further back to Multics if not earlier systems); it is short for index node, as the inode number is used to index into an array of on-disk inodes in order to ﬁnd the inode of that number. As we’ll see, design of the inode is one key part of ﬁle system design. Most modern systems have some kind of structure like this for every ﬁle they track, but perhaps call them different things (such as dnodes, fnodes, etc.).

Each inode is implicitly referred to by a number (called the i-number), which we’ve earlier called the low-level name of the ﬁle. In vsfs (and other simple ﬁle systems), given an i-number, you should directly be able to calculate where on the disk the corresponding inode is located. For example, take the inode table of vsfs as above: 20KB in size (ﬁve 4KB blocks) and thus consisting of 80 inodes (assuming each inode is 256 bytes); further assume that the inode region starts at 12KB (i.e, the superblock starts at 0KB, the inode bitmap is at address 4KB, the data bitmap at 8KB, and thus the inode table comes right after). In vsfs, we thus have the following layout for the beginning of the ﬁle system partition (in closeup view):

Super i-bmap d-bmap

0KB 4KB 8KB 12KB 16KB 20KB 24KB 28KB 32KB

The Inode Table (Closeup)

0 1 2 3 4 5 6 7 8 9 1011 12131415

16171819 20212223 24252627 28293031

32333435 36373839 40414243 44454647

48495051 52535455 56575859 60616263

64656667 68697071 72737475 76777879

iblock 0 iblock 1 iblock 2 iblock 3 iblock 4

To read inode number 32, the ﬁle system would ﬁrst calculate the offset into the inode region (32 · sizeof(inode) or 8192), add it to the start address of the inode table on disk (inodeStartAddr = 12KB), and thus arrive upon the correct byte address of the desired block of inodes: 20KB. Recall that disks are not byte addressable, but rather consist of a large number of addressable sectors, usually 512 bytes. Thus, to fetch the block of inodes that contains inode 32, the ﬁle system would issue a read to sector 20×1024

512 , or 40, to fetch the desired inode block. More generally, the sector address sector of the inode block can be calculated as follows:

blk = (inumber * sizeof(inode_t)) / blockSize; sector = ((blk * blockSize) + inodeStartAddr) / sectorSize;

Inside each inode is virtually all of the information you need about a ﬁle: its type (e.g., regular ﬁle, directory, etc.), its size, the number of blocks allocated to it, protection information (such as who owns the ﬁle, as well

EASY PIECES

Size Name What is this inode ﬁeld for? 2 mode can this ﬁle be read/written/executed? 2 uid who owns this ﬁle? 4 size how many bytes are in this ﬁle? 4 time what time was this ﬁle last accessed? 4 ctime what time was this ﬁle’s inode changed? 4 mtime what time was this ﬁle last modiﬁed? 4 dtime what time was this inode deleted? 2 gid which group does this ﬁle belong to? 2 links count how many hard links are there to this ﬁle? 4 blocks how many blocks have been allocated to this ﬁle? 4 ﬂags how should ext2 use this inode? 4 osd1 an OS-dependent ﬁeld 60 block a set of disk pointers (15 total) 4 generation ﬁle version (used by NFS) 4 ﬁle acl a new permissions model beyond mode bits 4 dir acl called access control lists

Figure 40.1: Simpliﬁed Ext2 Inode

as who can access it), some time information, including when the ﬁle was created, modiﬁed, or last accessed, as well as information about where its data blocks reside on disk (e.g., pointers of some kind). We refer to all such information about a ﬁle as metadata; in fact, any information inside the ﬁle system that isn’t pure user data is often referred to as such. An example inode from ext2 [P09] is shown in Figure 40.11.

One of the most important decisions in the design of the inode is how it refers to where data blocks are. One simple approach would be to have one or more direct pointers (disk addresses) inside the inode; each pointer refers to one disk block that belongs to the ﬁle. Such an approach is limited: for example, if you want to have a ﬁle that is really big (e.g., bigger than the block size multiplied by the number of direct pointers in the inode), you are out of luck.

The Multi-Level Index

To support bigger ﬁles, ﬁle system designers have had to introduce different structures within inodes. One common idea is to have a special pointer known as an indirect pointer. Instead of pointing to a block that contains user data, it points to a block that contains more pointers, each of which point to user data. Thus, an inode may have some ﬁxed number of direct pointers (e.g., 12), and a single indirect pointer. If a ﬁle grows large enough, an indirect block is allocated (from the data-block region of the disk), and the inode’s slot for an indirect pointer is set to point to it. Assuming 4-KB blocks and 4-byte disk addresses, that adds another 1024 pointers; the ﬁle can grow to be (12 + 1024) · 4K or 4144KB.

1Type info is kept in the directory entry, and thus is not found in the inode itself.

TIP: CONSIDER EXTENT-BASED APPROACHES A different approach is to use extents instead of pointers. An extent is simply a disk pointer plus a length (in blocks); thus, instead of requiring a pointer for every block of a ﬁle, all one needs is a pointer and a length to specify the on-disk location of a ﬁle. Just a single extent is limiting, as one may have trouble ﬁnding a contiguous chunk of on-disk free space when allocating a ﬁle. Thus, extent-based ﬁle systems often allow for more than one extent, thus giving more freedom to the ﬁle system during ﬁle allocation.

In comparing the two approaches, pointer-based approaches are the most ﬂexible but use a large amount of metadata per ﬁle (particularly for large ﬁles). Extent-based approaches are less ﬂexible but more compact; in particular, they work well when there is enough free space on the disk and ﬁles can be laid out contiguously (which is the goal for virtually any ﬁle allocation policy anyhow).

Not surprisingly, in such an approach, you might want to support even larger ﬁles. To do so, just add another pointer to the inode: the double indirect pointer. This pointer refers to a block that contains pointers to indirect blocks, each of which contain pointers to data blocks. A double indirect block thus adds the possibility to grow ﬁles with an additional 1024 · 1024 or 1-million 4KB blocks, in other words supporting ﬁles that are over 4GB in size. You may want even more, though, and we bet you know where this is headed: the triple indirect pointer.

Overall, this imbalanced tree is referred to as the multi-level index approach to pointing to ﬁle blocks. Let’s examine an example with twelve direct pointers, as well as both a single and a double indirect block. Assuming a block size of 4 KB, and 4-byte pointers, this structure can accommodate a ﬁle of just over 4 GB in size (i.e., (12 + 1024 + 10242) × 4 KB). Can you ﬁgure out how big of a ﬁle can be handled with the addition of a triple-indirect block? (hint: pretty big)

Many ﬁle systems use a multi-level index, including commonly-used ﬁle systems such as Linux ext2 [P09] and ext3, NetApp’s WAFL, as well as the original UNIX ﬁle system. Other ﬁle systems, including SGI XFS and Linux ext4, use extents instead of simple pointers; see the earlier aside for details on how extent-based schemes work (they are akin to segments in the discussion of virtual memory).

You might be wondering: why use an imbalanced tree like this? Why not a different approach? Well, as it turns out, many researchers have studied ﬁle systems and how they are used, and virtually every time they ﬁnd certain “truths” that hold across the decades. One such ﬁnding is that most ﬁles are small. This imbalanced design reﬂects such a reality; if most ﬁles are indeed small, it makes sense to optimize for this case. Thus, with a small number of direct pointers (12 is a typical number), an inode

EASY PIECES

Most ﬁles are small ˜2K is the most common size Average ﬁle size is growing Almost 200K is the average Most bytes are stored in large ﬁles A few big ﬁles use most of space File systems contain lots of ﬁles Almost 100K on average File systems are roughly half full Even as disks grow, ﬁle systems remain ˜50% full Directories are typically small Many have few entries; most have 20 or fewer

Figure 40.2: File System Measurement Summary

can directly point to 48 KB of data, needing one (or more) indirect blocks for larger ﬁles. See Agrawal et. al [A+07] for a recent-ish study; Figure 40.2 summarizes those results. Of course, in the space of inode design, many other possibilities exist; after all, the inode is just a data structure, and any data structure that stores the relevant information, and can query it effectively, is sufﬁcient. As ﬁle system software is readily changed, you should be willing to explore different designs should workloads or technologies change.

40.4 Directory Organization

In vsfs (as in many ﬁle systems), directories have a simple organization; a directory basically just contains a list of (entry name, inode number) pairs. For each ﬁle or directory in a given directory, there is a string and a number in the data block(s) of the directory. For each string, there may also be a length (assuming variable-sized names).

For example, assume a directory dir (inode number 5) has three ﬁles in it (foo, bar, and foobar_is_a_pretty_longname), with inode numbers 12, 13, and 24 respectively. The on-disk data for dir might look like:

inum | reclen | strlen | name

5 12 2 . 2 12 3 .. 12 12 4 foo 13 12 4 bar 24 36 28 foobar_is_a_pretty_longname

In this example, each entry has an inode number, record length (the total bytes for the name plus any left over space), string length (the actual length of the name), and ﬁnally the name of the entry. Note that each directory has two extra entries, . “dot” and .. “dot-dot”; the dot directory is just the current directory (in this example, dir), whereas dot-dot is the parent directory (in this case, the root).

Deleting a ﬁle (e.g., calling unlink()) can leave an empty space in the middle of the directory, and hence there should be some way to mark that as well (e.g., with a reserved inode number such as zero). Such a

ASIDE: LINKED-BASED APPROACHES Another simpler approach in designing inodes is to use a linked list. Thus, inside an inode, instead of having multiple pointers, you just need one, to point to the ﬁrst block of the ﬁle. To handle larger ﬁles, add another pointer at the end of that data block, and so on, and thus you can support large ﬁles. As you might have guessed, linked ﬁle allocation performs poorly for some workloads; think about reading the last block of a ﬁle, for example, or just doing random access. Thus, to make linked allocation work better, some systems will keep an in-memory table of link information, instead of storing the next pointers with the data blocks themselves. The table is indexed by the address of a data block D; the content of an entry is simply D’s next pointer, i.e., the address of the next block in a ﬁle which follows D. A null-value could be there too (indicating an end-of-ﬁle), or some other marker to indicate that a particular block is free. Having such a table of next pointers makes it so that a linked allocation scheme can effectively do random ﬁle accesses, simply by ﬁrst scanning through the (in memory) table to ﬁnd the desired block, and then accessing (on disk) it directly. Does such a table sound familiar? What we have described is the basic structure of what is known as the ﬁle allocation table, or FAT ﬁle system. Yes, this classic old Windows ﬁle system, before NTFS [C94], is based on a simple linked-based allocation scheme. There are other differences from a standard UNIX ﬁle system too; for example, there are no inodes per se, but rather directory entries which store metadata about a ﬁle and refer directly to the ﬁrst block of said ﬁle, which makes creating hard links impossible. See Brouwer [B02] for more of the inelegant details.

delete is one reason the record length is used: a new entry may reuse an old, bigger entry and thus have extra space within.

You might be wondering where exactly directories are stored. Often, ﬁle systems treat directories as a special type of ﬁle. Thus, a directory has an inode, somewhere in the inode table (with the type ﬁeld of the inode marked as “directory” instead of “regular ﬁle”). The directory has data blocks pointed to by the inode (and perhaps, indirect blocks); these data blocks live in the data block region of our simple ﬁle system. Our on-disk structure thus remains unchanged.

We should also note again that this simple linear list of directory entries is not the only way to store such information. As before, any data structure is possible. For example, XFS [S+96] stores directories in B-tree form, making ﬁle create operations (which have to ensure that a ﬁle name has not been used before creating it) faster than systems with simple lists that must be scanned in their entirety.

EASY PIECES

ASIDE: FREE SPACE MANAGEMENT There are many ways to manage free space; bitmaps are just one way. Some early ﬁle systems used free lists, where a single pointer in the super block was kept to point to the ﬁrst free block; inside that block the next free pointer was kept, thus forming a list through the free blocks of the system. When a block was needed, the head block was used and the list updated accordingly. Modern ﬁle systems use more sophisticated data structures. For example, SGI’s XFS [S+96] uses some form of a B-tree to compactly represent which chunks of the disk are free. As with any data structure, different timespace trade-offs are possible.

40.5 Free Space Management

A ﬁle system must track which inodes and data blocks are free, and which are not, so that when a new ﬁle or directory is allocated, it can ﬁnd space for it. Thus free space management is important for all ﬁle systems. In vsfs, we have two simple bitmaps for this task.

For example, when we create a ﬁle, we will have to allocate an inode for that ﬁle. The ﬁle system will thus search through the bitmap for an inode that is free, and allocate it to the ﬁle; the ﬁle system will have to mark the inode as used (with a 1) and eventually update the on-disk bitmap with the correct information. A similar set of activities take place when a data block is allocated.

Some other considerations might also come into play when allocating data blocks for a new ﬁle. For example, some Linux ﬁle systems, such as ext2 and ext3, will look for a sequence of blocks (say 8) that are free when a new ﬁle is created and needs data blocks; by ﬁnding such a sequence of free blocks, and then allocating them to the newly-created ﬁle, the ﬁle system guarantees that a portion of the ﬁle will be contiguous on the disk, thus improving performance. Such a pre-allocation policy is thus a commonly-used heuristic when allocating space for data blocks.

40.6 Access Paths: Reading and Writing

Now that we have some idea of how ﬁles and directories are stored on disk, we should be able to follow the ﬂow of operation during the activity of reading or writing a ﬁle. Understanding what happens on this access path is thus the second key in developing an understanding of how a ﬁle system works; pay attention!

For the following examples, let us assume that the ﬁle system has been mounted and thus that the superblock is already in memory. Everything else (i.e., inodes, directories) is still on the disk.

data inode root foo bar root foo bar bar bar bitmap bitmap inode inode inode data data data data data

[0] [1] [2] read

read open(bar) read

read read read read() read write

read read() read write

read read() read write

Figure 40.3: File Read Timeline (Time Increasing Downward)

Reading A File From Disk

In this simple example, let us ﬁrst assume that you want to simply open a ﬁle (e.g., /foo/bar), read it, and then close it. For this simple example, let’s assume the ﬁle is just 12KB in size (i.e., 3 blocks).

When you issue an open("/foo/bar", O_RDONLY) call, the ﬁle system ﬁrst needs to ﬁnd the inode for the ﬁle bar, to obtain some basic information about the ﬁle (permissions information, ﬁle size, etc.). To do so, the ﬁle system must be able to ﬁnd the inode, but all it has right now is the full pathname. The ﬁle system must traverse the pathname and thus locate the desired inode.

All traversals begin at the root of the ﬁle system, in the root directory which is simply called /. Thus, the ﬁrst thing the FS will read from disk is the inode of the root directory. But where is this inode? To ﬁnd an inode, we must know its i-number. Usually, we ﬁnd the i-number of a ﬁle or directory in its parent directory; the root has no parent (by deﬁnition). Thus, the root inode number must be “well known”; the FS must know what it is when the ﬁle system is mounted. In most UNIX ﬁle systems, the root inode number is 2. Thus, to begin the process, the FS reads in the block that contains inode number 2 (the ﬁrst inode block).

Once the inode is read in, the FS can look inside of it to ﬁnd pointers to data blocks, which contain the contents of the root directory. The FS will thus use these on-disk pointers to read through the directory, in this case looking for an entry for foo. By reading in one or more directory data blocks, it will ﬁnd the entry for foo; once found, the FS will also have found the inode number of foo (say it is 44) which it will need next.

The next step is to recursively traverse the pathname until the desired inode is found. In this example, the FS reads the block containing the

EASY PIECES

ASIDE: READS DON’T ACCESS ALLOCATION STRUCTURES We’ve seen many students get confused by allocation structures such as bitmaps. In particular, many often think that when you are simply reading a ﬁle, and not allocating any new blocks, that the bitmap will still be consulted. This is not true! Allocation structures, such as bitmaps, are only accessed when allocation is needed. The inodes, directories, and indirect blocks have all the information they need to complete a read request; there is no need to make sure a block is allocated when the inode already points to it.

inode of foo and then its directory data, ﬁnally ﬁnding the inode number of bar. The ﬁnal step of open() is to read bar’s inode into memory; the FS then does a ﬁnal permissions check, allocates a ﬁle descriptor for this process in the per-process open-ﬁle table, and returns it to the user.

Once open, the program can then issue a read() system call to read from the ﬁle. The ﬁrst read (at offset 0 unless lseek() has been called) will thus read in the ﬁrst block of the ﬁle, consulting the inode to ﬁnd the location of such a block; it may also update the inode with a new lastaccessed time. The read will further update the in-memory open ﬁle table for this ﬁle descriptor, updating the ﬁle offset such that the next read will read the second ﬁle block, etc.

At some point, the ﬁle will be closed. There is much less work to be done here; clearly, the ﬁle descriptor should be deallocated, but for now, that is all the FS really needs to do. No disk I/Os take place.

A depiction of this entire process is found in Figure 40.3 (page 11); time increases downward in the ﬁgure. In the ﬁgure, the open causes numerous reads to take place in order to ﬁnally locate the inode of the ﬁle. Afterwards, reading each block requires the ﬁle system to ﬁrst consult the inode, then read the block, and then update the inode’s last-accessed-time ﬁeld with a write. Spend some time and understand what is going on.

Also note that the amount of I/O generated by the open is proportional to the length of the pathname. For each additional directory in the path, we have to read its inode as well as its data. Making this worse would be the presence of large directories; here, we only have to read one block to get the contents of a directory, whereas with a large directory, we might have to read many data blocks to ﬁnd the desired entry. Yes, life can get pretty bad when reading a ﬁle; as you’re about to ﬁnd out, writing out a ﬁle (and especially, creating a new one) is even worse.

Writing A File To Disk Writing to a ﬁle is a similar process. First, the ﬁle must be opened (as above). Then, the application can issue write() calls to update the ﬁle with new contents. Finally, the ﬁle is closed.

Unlike reading, writing to the ﬁle may also allocate a block (unless the block is being overwritten, for example). When writing out a new ﬁle, each write not only has to write data to disk but has to ﬁrst decide

data inode root foo bar root foo bar bar bar bitmap bitmap inode inode inode data data data data data [0] [1] [2] read

read read

read create read (/foo/bar) write

write read write write

read read write() write

write write

read read write() write

write write

read read write() write

write write

Figure 40.4: File Creation Timeline (Time Increasing Downward)

which block to allocate to the ﬁle and thus update other structures of the disk accordingly (e.g., the data bitmap and inode). Thus, each write to a ﬁle logically generates ﬁve I/Os: one to read the data bitmap (which is then updated to mark the newly-allocated block as used), one to write the bitmap (to reﬂect its new state to disk), two more to read and then write the inode (which is updated with the new block’s location), and ﬁnally one to write the actual block itself.

The amount of write trafﬁc is even worse when one considers a simple and common operation such as ﬁle creation. To create a ﬁle, the ﬁle system must not only allocate an inode, but also allocate space within the directory containing the new ﬁle. The total amount of I/O trafﬁc to do so is quite high: one read to the inode bitmap (to ﬁnd a free inode), one write to the inode bitmap (to mark it allocated), one write to the new inode itself (to initialize it), one to the data of the directory (to link the high-level name of the ﬁle to its inode number), and one read and write to the directory inode to update it. If the directory needs to grow to accommodate the new entry, additional I/Os (i.e., to the data bitmap, and the new directory block) will be needed too. All that just to create a ﬁle!

EASY PIECES

Let’s look at a speciﬁc example, where the ﬁle /foo/bar is created, and three blocks are written to it. Figure 40.4 (page 13) shows what happens during the open() (which creates the ﬁle) and during each of three 4KB writes. In the ﬁgure, reads and writes to the disk are grouped under which system call caused them to occur, and the rough ordering they might take place in goes from top to bottom of the ﬁgure. You can see how much work it is to create the ﬁle: 10 I/Os in this case, to walk the pathname and then ﬁnally create the ﬁle2. You can also see that each allocating write costs 5 I/Os: a pair to read and update the inode, another pair to read and update the data bitmap, and then ﬁnally the write of the data itself. How can a ﬁle system accomplish any of this with reasonable efﬁciency?

THE CRUX: HOW TO REDUCE FILE SYSTEM I/O COSTS Even the simplest of operations like opening, reading, or writing a ﬁle incurs a huge number of I/O operations, scattered over the disk. What can a ﬁle system do to reduce the high costs of doing so many I/Os?

40.7 Caching and Buffering

As the examples above show, reading and writing ﬁles can be expensive, incurring many I/Os to the (slow) disk. To remedy what would clearly be a huge performance problem, most ﬁle systems aggressively use system memory (DRAM) to cache important blocks.

Imagine the open example above: without caching, every ﬁle open would require at least two reads for every level in the directory hierarchy (one to read the inode of the directory in question, and at least one to read its data). With a long pathname (e.g., /1/2/3/ ... /100/ﬁle.txt), the ﬁle system would literally perform hundreds of reads just to open the ﬁle!

Early ﬁle systems thus introduced a ﬁxed-size cache to hold popular blocks. As in our discussion of virtual memory, strategies such as LRU and different variants would decide which blocks to keep in cache. This ﬁxed-size cache would usually be allocated at boot time to be roughly 10% of total memory. This static partitioning of memory, however, can be wasteful; what if the ﬁle system doesn’t need 10% of memory at a given point in time? With the ﬁxed-size approach described above, unused pages in the ﬁle cache cannot be re-purposed for some other use, and thus go to waste.

Modern systems, in contrast, employ a dynamic partitioning approach. Speciﬁcally, many modern operating systems integrate virtual memory pages and ﬁle system pages into a uniﬁed page cache [S00]. In this way,

2One surprise here is that there is a read associated with the creation of the bar inode, even though it is not yet initialized; can you guess why? (think...) Answer: this read occurs because an inode (which is small) is contained within a larger block (e.g., 4KB). Thus, the system performs a read-modify-write to update the newly allocated inode within the block.

TIP: UNDERSTAND STATIC VS. DYNAMIC PARTITIONING When dividing a resource among different clients/users, you can use either static partitioning or dynamic partitioning. The static approach simply divides the resource into ﬁxed proportions once; for example, if there are two possible users of memory, you can give some ﬁxed fraction of memory to one user, and the rest to the other. The dynamic approach is more ﬂexible, giving out differing amounts of the resource over time; for example, one user may get a higher percentage of disk bandwidth for a period of time, but then later, the system may switch and decide to give a different user a larger fraction of available disk bandwidth.

Each approach has its advantages. Static partitioning ensures each user receives some share of the resource, usually delivers more predictable performance, and is often easier to implement. Dynamic partitioning can achieve better utilization (by letting resource-hungry users consume otherwise idle resources), but can be more complex to implement, and can lead to worse performance for users whose idle resources get consumed by others and then take a long time to reclaim when needed. As is often the case, there is no best method; rather, you should think about the problem at hand and decide which approach is most suitable. Indeed, shouldn’t you always be doing that?

memory can be allocated more ﬂexibly across virtual memory and ﬁle system, depending on which needs more memory at a given time.

Now imagine the ﬁle open example with caching. The ﬁrst open may generate a lot of I/O trafﬁc to read in directory inode and data, but subsequent ﬁle opens of that same ﬁle (or ﬁles in the same directory) will mostly hit in the cache and thus no I/O is needed.

Let us also consider the effect of caching on writes. Whereas read I/O can be avoided altogether with a sufﬁciently large cache, write trafﬁc has to go to disk in order to become persistent. Thus, a cache does not serve as the same kind of ﬁlter on write trafﬁc that it does for reads. That said, write buffering (as it is sometimes called) certainly has a number of performance beneﬁts. First, by delaying writes, the ﬁle system can batch some updates into a smaller set of I/Os; for example, if an inode bitmap is updated when one ﬁle is created and then updated moments later as another ﬁle is created, the ﬁle system saves an I/O by delaying the write after the ﬁrst update. Second, by buffering a number of writes in memory, the system can then schedule the subsequent I/Os and thus increase performance. Finally, some writes are avoided altogether by delaying them; for example, if an application creates a ﬁle and then deletes it, delaying the writes to reﬂect the ﬁle creation to disk avoids them entirely. In this case, laziness (in writing blocks to disk) is a virtue.

For the reasons above, most modern ﬁle systems buffer writes in memory for anywhere between ﬁve and thirty seconds, representing yet another trade-off: if the system crashes before the updates have been prop-

EASY PIECES

TIP: UNDERSTAND THE DURABILITY/PERFORMANCE TRADE-OFF Storage systems often present a durability/performance trade-off to users. If the user wishes data that is written to be immediately durable, the system must go through the full effort of committing the newlywritten data to disk, and thus the write is slow (but safe). However, if the user can tolerate the loss of a little data, the system can buffer writes in memory for some time and write them later to the disk (in the background). Doing so makes writes appear to complete quickly, thus improving perceived performance; however, if a crash occurs, writes not yet committed to disk will be lost, and hence the trade-off. To understand how to make this trade-off properly, it is best to understand what the application using the storage system requires; for example, while it may be tolerable to lose the last few images downloaded by your web browser, losing part of a database transaction that is adding money to your bank account may be less tolerable. Unless you’re rich, of course; in that case, why do you care so much about hoarding every last penny?

agated to disk, the updates are lost; however, by keeping writes in memory longer, performance can be improved by batching, scheduling, and even avoiding writes.

Some applications (such as databases) don’t enjoy this trade-off. Thus, to avoid unexpected data loss due to write buffering, they simply force writes to disk, by calling fsync(), by using direct I/O interfaces that work around the cache, or by using the raw disk interface and avoiding the ﬁle system altogether3. While most applications live with the tradeoffs made by the ﬁle system, there are enough controls in place to get the system to do what you want it to, should the default not be satisfying.

40.8 Summary

We have seen the basic machinery required in building a ﬁle system. There needs to be some information about each ﬁle (metadata), usually stored in a structure called an inode. Directories are just a speciﬁc type of ﬁle that store name→inode-number mappings. And other structures are needed too; for example, ﬁle systems often use a structure such as a bitmap to track which inodes or data blocks are free or allocated.

The terriﬁc aspect of ﬁle system design is its freedom; the ﬁle systems we explore in the coming chapters each take advantage of this freedom to optimize some aspect of the ﬁle system. There are also clearly many policy decisions we have left unexplored. For example, when a new ﬁle is created, where should it be placed on disk? This policy and others will also be the subject of future chapters. Or will they?4

3Take a database class to learn more about old-school databases and their former insistence on avoiding the OS and controlling everything themselves. But watch out! Those database types are always trying to bad mouth the OS. Shame on you, database people. Shame.

4Cue mysterious music that gets you even more intrigued about the topic of ﬁle systems.
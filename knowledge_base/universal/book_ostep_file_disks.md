# Hard Disk Drives (including disk scheduling) (Operating Systems: Three Easy Pieces)

Source URL: https://pages.cs.wisc.edu/~remzi/OSTEP/file-disks.pdf
Source: Hard Disk Drives (including disk scheduling) (Operating Systems: Three Easy Pieces)
Licence: Free online textbook by the authors; downloaded for personal study, not redistributed
Retrieved: 2026-10-23

Hard Disk Drives

The last chapter introduced the general concept of an I/O device and showed you how the OS might interact with such a beast. In this chapter, we dive into more detail about one device in particular: the hard disk drive. These drives have been the main form of persistent data storage in computer systems for decades and much of the development of ﬁle system technology (coming soon) is predicated on their behavior. Thus, it is worth understanding the details of a disk’s operation before building the ﬁle system software that manages it. Many of these details are available in excellent papers by Ruemmler and Wilkes [RW92] and Anderson, Dykes, and Riedel [ADR03].

CRUX: HOW TO STORE AND ACCESS DATA ON DISK How do modern hard-disk drives store data? What is the interface? How is the data actually laid out and accessed? How does disk scheduling improve performance?

37.1 The Interface

Let’s start by understanding the interface to a modern disk drive. The basic interface for all modern drives is straightforward. The drive consists of a large number of sectors (512-byte blocks), each of which can be read or written. The sectors are numbered from 0 to n −1 on a disk with n sectors. Thus, we can view the disk as an array of sectors; 0 to n −1 is thus the address space of the drive.

Multi-sector operations are possible; indeed, many ﬁle systems will read or write 4KB at a time (or more). However, when updating the disk, the only guarantee drive manufacturers make is that a single 512-byte write is atomic (i.e., it will either complete in its entirety or it won’t complete at all); thus, if an untimely power loss occurs, only a portion of a larger write may complete (sometimes called a torn write).

There are some assumptions most clients of disk drives make, but that are not speciﬁed directly in the interface; Schlosser and Ganger have

11 10 9 8 7

5 4 3 2 1

Spindle

Figure 37.1: A Disk With Just A Single Track

called this the “unwritten contract” of disk drives [SG04]. Speciﬁcally, one can usually assume that accessing two blocks1 near one-another within the drive’s address space will be faster than accessing two blocks that are far apart. One can also usually assume that accessing blocks in a contiguous chunk (i.e., a sequential read or write) is the fastest access mode, and usually much faster than any more random access pattern.

37.2 Basic Geometry

Let’s start to understand some of the components of a modern disk. We start with a platter, a circular hard surface on which data is stored persistently by inducing magnetic changes to it. A disk may have one or more platters; each platter has 2 sides, each of which is called a surface. These platters are usually made of some hard material (such as aluminum), and then coated with a thin magnetic layer that enables the drive to persistently store bits even when the drive is powered off.

The platters are all bound together around the spindle, which is connected to a motor that spins the platters around (while the drive is powered on) at a constant (ﬁxed) rate. The rate of rotation is often measured in rotations per minute (RPM), and typical modern values are in the 7,200 RPM to 15,000 RPM range. Note that we will often be interested in the time of a single rotation, e.g., a drive that rotates at 10,000 RPM means that a single rotation takes about 6 milliseconds (6 ms).

Data is encoded on each surface in concentric circles of sectors; we call one such concentric circle a track. A single surface contains many thousands and thousands of tracks, tightly packed together, with hundreds of tracks ﬁtting into the width of a human hair.

To read and write from the surface, we need a mechanism that allows us to either sense (i.e., read) the magnetic patterns on the disk or to induce a change in (i.e., write) them. This process of reading and writing is accomplished by the disk head; there is one such head per surface of the drive. The disk head is attached to a single disk arm, which moves across the surface to position the head over the desired track.

1We, and others, often use the terms block and sector interchangeably, assuming the reader will know exactly what is meant per context. Sorry about this!

Head

Arm

11 10 9 8 7

5 4 3 2 1

Spindle

Rotates this way

Figure 37.2: A Single Track Plus A Head

37.3 A Simple Disk Drive

Let’s understand how disks work by building up a model one track at a time. Assume we have a simple disk with a single track (Figure 37.1). This track has just 12 sectors, each of which is 512 bytes in size (our typical sector size, recall) and addressed therefore by the numbers 0 through 11. The single platter we have here rotates around the spindle, to which a motor is attached.

Of course, the track by itself isn’t too interesting; we want to be able to read or write those sectors, and thus we need a disk head, attached to a disk arm, as we now see (Figure 37.2). In the ﬁgure, the disk head, attached to the end of the arm, is positioned over sector 6, and the surface is rotating counter-clockwise.

Single-track Latency: The Rotational Delay To understand how a request would be processed on our simple, onetrack disk, imagine we now receive a request to read block 0. How should the disk service this request?

In our simple disk, the disk doesn’t have to do much. In particular, it must just wait for the desired sector to rotate under the disk head. This wait happens often enough in modern drives, and is an important enough component of I/O service time, that it has a special name: rotational delay (sometimes rotation delay, though that sounds weird). In the example, if the full rotational delay is R, the disk has to incur a rotational delay of about R

2 to wait for 0 to come under the read/write head (if we start at 6). A worst-case request on this single track would be to sector 5, causing nearly a full rotational delay in order to service such a request.

Multiple Tracks: Seek Time So far our disk just has a single track, which is not too realistic; modern disks of course have many millions. Let’s thus look at an ever-so-slightly more realistic disk surface, this one with three tracks (Figure 37.3, left).

In the ﬁgure, the head is currently positioned over the innermost track (which contains sectors 24 through 35); the next track over contains the

EASY PIECES

10 9 8

4 3 2

22 21 20

16 15 14

35 34 33 32 31

29 28 27 26 25

Spindle

Rotates this way

Seek

Remaining rotation

1 0 11

7 6 5

13 12 23

19 18 17

26 25 24 35 34

32 31 30 29 28

Spindle

Rotates this way

Figure 37.3: Three Tracks Plus A Head (Right: With Seek) next set of sectors (12 through 23), and the outermost track contains the ﬁrst sectors (0 through 11).

To understand how the drive might access a given sector, we now trace what would happen on a request to a distant sector, e.g., a read to sector 11. To service this read, the drive has to ﬁrst move the disk arm to the correct track (in this case, the outermost one), in a process known as a seek. Seeks, along with rotations, are one of the most costly disk operations.

The seek, it should be noted, has many phases: ﬁrst an acceleration phase as the disk arm gets moving; then coasting as the arm is moving at full speed, then deceleration as the arm slows down; ﬁnally settling as the head is carefully positioned over the correct track. The settling time is often quite signiﬁcant, e.g., 0.5 to 2 ms, as the drive must be certain to ﬁnd the right track (imagine if it just got close instead!).

After the seek, the disk arm has positioned the head over the right track. A depiction of the seek is found in Figure 37.3 (right).

As we can see, during the seek, the arm has been moved to the desired track, and the platter of course has rotated, in this case about 3 sectors. Thus, sector 9 is just about to pass under the disk head, and we must only endure a short rotational delay to complete the transfer.

When sector 11 passes under the disk head, the ﬁnal phase of I/O will take place, known as the transfer, where data is either read from or written to the surface. And thus, we have a complete picture of I/O time: ﬁrst a seek, then waiting for the rotational delay, and ﬁnally the transfer.

Some Other Details

Though we won’t spend too much time on it, there are some other interesting details about how hard drives operate. Many drives employ some kind of track skew to make sure that sequential reads can be properly serviced even when crossing track boundaries. In our simple example disk, this might appear as seen in Figure 37.4 (page 5).

Track skew: 2 blocks

10 9 8

4 3 2

20 19 18

14 13 12

31 30 29 28 27

25 24 35 34 33

Spindle

Rotates this way

Figure 37.4: Three Tracks: Track Skew Of 2

Sectors are often skewed like this because when switching from one track to another, the disk needs time to reposition the head (even to neighboring tracks). Without such skew, the head would be moved to the next track but the desired next block would have already rotated under the head, and thus the drive would have to wait almost the entire rotational delay to access the next block.

Another reality is that outer tracks tend to have more sectors than inner tracks, which is a result of geometry; there is simply more room out there. These tracks are often referred to as multi-zoned disk drives, where the disk is organized into multiple zones, and where a zone is consecutive set of tracks on a surface. Each zone has the same number of sectors per track, and outer zones have more sectors than inner zones.

Finally, an important part of any modern disk drive is its cache, for historical reasons sometimes called a track buffer. This cache is just some small amount of memory (usually around 8 or 16 MB) which the drive can use to hold data read from or written to the disk. For example, when reading a sector from the disk, the drive might decide to read in all of the sectors on that track and cache them in its memory; doing so allows the drive to quickly respond to any subsequent requests to the same track.

On writes, the drive has a choice: should it acknowledge the write has completed when it has put the data in its memory, or after the write has actually been written to disk? The former is called write back caching (or sometimes immediate reporting), and the latter write through. Write back caching sometimes makes the drive appear “faster”, but can be dangerous; if the ﬁle system or applications require that data be written to disk in a certain order for correctness, write-back caching can lead to problems (read the chapter on ﬁle-system journaling for details).

EASY PIECES

ASIDE: DIMENSIONAL ANALYSIS Remember in Chemistry class, how you solved virtually every problem by simply setting up the units such that they canceled out, and somehow the answers popped out as a result? That chemical magic is known by the highfalutin name of dimensional analysis and it turns out it is useful in computer systems analysis too. Let’s do an example to see how dimensional analysis works and why it is useful. In this case, assume you have to ﬁgure out how long, in milliseconds, a single rotation of a disk takes. Unfortunately, you are given only the RPM of the disk, or rotations per minute. Let’s assume we’re talking about a 10K RPM disk (i.e., it rotates 10,000 times per minute). How do we set up the dimensional analysis so that we get time per rotation in milliseconds? To do so, we start by putting the desired units on the left; in this case, we wish to obtain the time (in milliseconds) per rotation, so that is exactly what we write down: T ime (ms) 1 Rotation . We then write down everything we know, making sure to cancel units where possible. First, we obtain

1 minute 10,000 Rotations (keeping rotation on the bottom, as that’s where it is on the left), then transform minutes into seconds with 60 seconds

1 minute , and then ﬁnally transform seconds in milliseconds with 1000 ms

1 second. The ﬁnal result is the following (with units nicely canceled):

T ime (ms)

1 Rot. = 1✘✘✘ minute 10,000 Rot. · 60✘✘✘ seconds 1✘✘✘ minute · 1000 ms

1✘✘✘ second = 60,000 ms 10,000 Rot. = 6 ms Rotation

As you can see from this example, dimensional analysis makes what seems intuitive into a simple and repeatable process. Beyond the RPM calculation above, it comes in handy with I/O analysis regularly. For example, you will often be given the transfer rate of a disk, e.g., 100 MB/second, and then asked: how long does it take to transfer a 512 KB block (in milliseconds)? With dimensional analysis, it’s easy:

T ime (ms)

1 Request = 512✟✟ KB 1 Request · 1✟✟ MB 1024✟✟ KB · 1✘✘✘ second 100✟✟ MB · 1000 ms

1✘✘✘ second = 5 ms Request

37.4 I/O Time: Doing The Math

Now that we have an abstract model of the disk, we can use a little analysis to better understand disk performance. In particular, we can now represent I/O time as the sum of three major components:

TI/O = Tseek + Trotation + Ttransfer (37.1)

Note that the rate of I/O (RI/O), which is often more easily used for

Cheetah 15K.5 Barracuda Capacity 300 GB 1 TB RPM 15,000 7,200 Average Seek 4 ms 9 ms Max Transfer 125 MB/s 105 MB/s Platters 4 4 Cache 16 MB 16/32 MB Connects via SCSI SATA Figure 37.5: Disk Drive Specs: SCSI Versus SATA

comparison between drives (as we will do below), is easily computed from the time. Simply divide the size of the transfer by the time it took:

RI/O = SizeT ransfer

TI/O

(37.2)

To get a better feel for I/O time, let us perform the following calculation. Assume there are two workloads we are interested in. The ﬁrst, known as the random workload, issues small (e.g., 4KB) reads to random locations on the disk. Random workloads are common in many important applications, including database management systems. The second, known as the sequential workload, simply reads a large number of sectors consecutively from the disk, without jumping around. Sequential access patterns are quite common and thus important as well.

To understand the difference in performance between random and sequential workloads, we need to make a few assumptions about the disk drive ﬁrst. Let’s look at a couple of modern disks from Seagate. The ﬁrst, known as the Cheetah 15K.5 [S09b], is a high-performance SCSI drive. The second, the Barracuda [S09a], is a drive built for capacity. Details on both are found in Figure 37.5.

As you can see, the drives have quite different characteristics, and in many ways nicely summarize two important components of the disk drive market. The ﬁrst is the “high performance” drive market, where drives are engineered to spin as fast as possible, deliver low seek times, and transfer data quickly. The second is the “capacity” market, where cost per byte is the most important aspect; thus, the drives are slower but pack as many bits as possible into the space available.

From these numbers, we can start to calculate how well the drives would do under our two workloads outlined above. Let’s start by looking at the random workload. Assuming each 4 KB read occurs at a random location on disk, we can calculate how long each such read would take. On the Cheetah:

Tseek = 4 ms, Trotation = 2 ms, Ttransfer = 30 microsecs (37.3)

The average seek time (4 milliseconds) is just taken as the average time reported by the manufacturer; note that a full seek (from one end of the

EASY PIECES

TIP: USE DISKS SEQUENTIALLY When at all possible, transfer data to and from disks in a sequential manner. If sequential is not possible, at least think about transferring data in large chunks: the bigger, the better. If I/O is done in little random pieces, I/O performance will suffer dramatically. Also, users will suffer. Also, you will suffer, knowing what suffering you have wrought with your careless random I/Os.

surface to the other) would likely take two or three times longer. The average rotational delay is calculated from the RPM directly. 15000 RPM is equal to 250 RPS (rotations per second); thus, each rotation takes 4 ms. On average, the disk will encounter a half rotation and thus 2 ms is the average time. Finally, the transfer time is just the size of the transfer over the peak transfer rate; here it is vanishingly small (30 microseconds; note that we need 1000 microseconds just to get 1 millisecond!).

Thus, from our equation above, TI/O for the Cheetah roughly equals 6 ms. To compute the rate of I/O, we just divide the size of the transfer by the average time, and thus arrive at RI/O for the Cheetah under the random workload of about 0.66 MB/s. The same calculation for the Barracuda yields a TI/O of about 13.2 ms, more than twice as slow, and thus a rate of about 0.31 MB/s.

Now let’s look at the sequential workload. Here we can assume there is a single seek and rotation before a very long transfer. For simplicity, assume the size of the transfer is 100 MB. Thus, TI/O for the Cheetah and Barracuda is about 800 ms and 950 ms, respectively. The rates of I/O are thus very nearly the peak transfer rates of 125 MB/s and 105 MB/s, respectively. Figure 37.6 summarizes these numbers.

Cheetah Barracuda RI/O Random 0.66 MB/s 0.31 MB/s RI/O Sequential 125 MB/s 105 MB/s Figure 37.6: Disk Drive Performance: SCSI Versus SATA

The ﬁgure shows us a number of important things. First, and most importantly, there is a huge gap in drive performance between random and sequential workloads, almost a factor of 200 or so for the Cheetah and more than a factor 300 difference for the Barracuda. And thus we arrive at the most obvious design tip in the history of computing.

A second, more subtle point: there is a large difference in performance between high-end “performance” drives and low-end “capacity” drives. For this reason (and others), people are often willing to pay top dollar for the former while trying to get the latter as cheaply as possible.

ASIDE: COMPUTING THE “AVERAGE” SEEK In many books and papers, you will see average disk-seek time cited as being roughly one-third of the full seek time. Where does this come from?

Turns out it arises from a simple calculation based on average seek distance, not time. Imagine the disk as a set of tracks, from 0 to N. The seek distance between any two tracks x and y is thus computed as the absolute value of the difference between them: |x −y|.

To compute the average seek distance, all you need to do is to ﬁrst add up all possible seek distances:

N X

x=0

N X

y=0

|x −y|. (37.4)

Then, divide this by the number of different possible seeks: N 2. To compute the sum, we’ll just use the integral form:

Z N

x=0

Z N

y=0

|x −y| dy dx. (37.5)

To compute the inner integral, let’s break out the absolute value:

Z x

y=0

(x −y) dy +

Z N

y=x

(y −x) dy. (37.6)

Solving this leads to (xy −1

2y2) x

0 + ( 1 2y2 −xy) N

x which can be simpliﬁed to (x2 −Nx + 1

2N 2). Now we have to compute the outer integral: Z N

x=0

(x2 −Nx + 1

2N 2) dx, (37.7)

which results in:

(1

3x3 −N 2 x2 + N 2

2 x)

N

0 = N 3

3 . (37.8)

Remember that we still have to divide by the total number of seeks (N 2) to compute the average seek distance: ( N3

3 )/(N 2) = 1 3N. Thus the average seek distance on a disk, over all possible seeks, is one-third the full distance. And now when you hear that an average seek is one-third of a full seek, you’ll know where it came from.

EASY PIECES

10 9 8

4 3 2

22 21 20

16 15 14

35 34 33 32 31

29 28 27 26 25

Spindle

Rotates this way

Figure 37.7: SSTF: Scheduling Requests 21 And 2

37.5 Disk Scheduling

Because of the high cost of I/O, the OS has historically played a role in deciding the order of I/Os issued to the disk. More speciﬁcally, given a set of I/O requests, the disk scheduler examines the requests and decides which one to schedule next [SCO90, JW91].

Unlike job scheduling, where the length of each job is usually unknown, with disk scheduling, we can make a good guess at how long a “job” (i.e., disk request) will take. By estimating the seek and possible rotational delay of a request, the disk scheduler can know how long each request will take, and thus (greedily) pick the one that will take the least time to service ﬁrst. Thus, the disk scheduler will try to follow the principle of SJF (shortest job ﬁrst) in its operation.

SSTF: Shortest Seek Time First

One early disk scheduling approach is known as shortest-seek-time-ﬁrst (SSTF) (also called shortest-seek-ﬁrst or SSF). SSTF orders the queue of I/O requests by track, picking requests on the nearest track to complete ﬁrst. For example, assuming the current position of the head is over the inner track, and we have requests for sectors 21 (middle track) and 2 (outer track), we would then issue the request to 21 ﬁrst, wait for it to complete, and then issue the request to 2 (Figure 37.7).

SSTF works well in this example, seeking to the middle track ﬁrst and then the outer track. However, SSTF is not a panacea, for the following reasons. First, the drive geometry is not available to the host OS; rather, it sees an array of blocks. Fortunately, this problem is rather easily ﬁxed. Instead of SSTF, an OS can simply implement nearest-block-ﬁrst (NBF), which schedules the request with the nearest block address next.

The second problem is more fundamental: starvation. Imagine in our example above if there were a steady stream of requests to the inner track, where the head currently is positioned. Requests to any other tracks would then be ignored completely by a pure SSTF approach. And thus the crux of the problem:

CRUX: HOW TO HANDLE DISK STARVATION How can we implement SSTF-like scheduling but avoid starvation?

Elevator (a.k.a. SCAN or C-SCAN)

The answer to this query was developed some time ago (see [CKR72] for example), and is relatively straightforward. The algorithm, originally called SCAN, simply moves back and forth across the disk servicing requests in order across the tracks. Let’s call a single pass across the disk (from outer to inner tracks, or inner to outer) a sweep. Thus, if a request comes for a block on a track that has already been serviced on this sweep of the disk, it is not handled immediately, but rather queued until the next sweep (in the other direction).

SCAN has a number of variants, all of which do about the same thing. For example, Coffman et al. introduced F-SCAN, which freezes the queue to be serviced when it is doing a sweep [CKR72]; this action places requests that come in during the sweep into a queue to be serviced later. Doing so avoids starvation of far-away requests, by delaying the servicing of late-arriving (but nearer by) requests.

C-SCAN is another common variant, short for Circular SCAN. Instead of sweeping in both directions across the disk, the algorithm only sweeps from outer-to-inner, and then resets at the outer track to begin again. Doing so is a bit more fair to inner and outer tracks, as pure backand-forth SCAN favors the middle tracks, i.e., after servicing the outer track, SCAN passes through the middle twice before coming back to the outer track again.

For reasons that should now be clear, the SCAN algorithm (and its cousins) is sometimes referred to as the elevator algorithm, because it behaves like an elevator which is either going up or down and not just servicing requests to ﬂoors based on which ﬂoor is closer. Imagine how annoying it would be if you were going down from ﬂoor 10 to 1, and somebody got on at 3 and pressed 4, and the elevator went up to 4 because it was “closer” than 1! As you can see, the elevator algorithm, when used in real life, prevents ﬁghts from taking place on elevators. In disks, it just prevents starvation.

Unfortunately, SCAN and its cousins do not represent the best scheduling technology. In particular, SCAN (or SSTF even) does not actually adhere as closely to the principle of SJF as they could. In particular, they ignore rotation. And thus, another crux:

EASY PIECES

CRUX: HOW TO ACCOUNT FOR DISK ROTATION COSTS How can we implement an algorithm that more closely approximates SJF by taking both seek and rotation into account?

SPTF: Shortest Positioning Time First

Before discussing shortest positioning time ﬁrst or SPTF scheduling (sometimes also called shortest access time ﬁrst or SATF), which is the solution to our problem, let us make sure we understand the problem in more detail. Figure 37.8 presents an example.

In the example, the head is currently positioned over sector 30 on the inner track. The scheduler thus has to decide: should it schedule sector 16 (on the middle track) or sector 8 (on the outer track) for its next request. So which should it service next?

The answer, of course, is “it depends”. In engineering, it turns out “it depends” is almost always the answer, reﬂecting that trade-offs are part of the life of the engineer; such maxims are also good in a pinch, e.g., when you don’t know an answer to your boss’s question, you might want to try this gem. However, it is almost always better to know why it depends, which is what we discuss here.

What it depends on here is the relative time of seeking as compared to rotation. If, in our example, seek time is much higher than rotational delay, then SSTF (and variants) are just ﬁne. However, imagine if seek is quite a bit faster than rotation. Then, in our example, it would make more sense to seek further to service request 8 on the outer track than it would to perform the shorter seek to the middle track to service 16, which has to rotate all the way around before passing under the disk head.

10 9 8

4 3 2

22 21 20

16 15 14

35 34 33 32 31

29 28 27 26 25

Spindle

Rotates this way

Figure 37.8: SSTF: Sometimes Not Good Enough

TIP: IT ALWAYS DEPENDS (LIVNY’S LAW) Almost any question can be answered with “it depends”, as our colleague Miron Livny always says. However, use with caution, as if you answer too many questions this way, people will stop asking you questions altogether. For example, somebody asks: “want to go to lunch?” You reply: “it depends, are you coming along?”

On modern drives, as we saw above, both seek and rotation are roughly equivalent (depending, of course, on the exact requests), and thus SPTF is useful and improves performance. However, it is even more difﬁcult to implement in an OS, which generally does not have a good idea where track boundaries are or where the disk head currently is (in a rotational sense). Thus, SPTF is usually performed inside a drive, described below.

Other Scheduling Issues

There are many other issues we do not discuss in this brief description of basic disk operation, scheduling, and related topics. One such issue is this: where is disk scheduling performed on modern systems? In older systems, the operating system did all the scheduling; after looking through the set of pending requests, the OS would pick the best one, and issue it to the disk. When that request completed, the next one would be chosen, and so forth. Disks were simpler then, and so was life.

In modern systems, disks can accommodate multiple outstanding requests, and have sophisticated internal schedulers themselves (which can implement SPTF accurately; inside the disk controller, all relevant details are available, including exact head position). Thus, the OS scheduler usually picks what it thinks the best few requests are (say 16) and issues them all to disk; the disk then uses its internal knowledge of head position and detailed track layout information to service said requests in the best possible (SPTF) order.

Another important related task performed by disk schedulers is I/O merging. For example, imagine a series of requests to read blocks 33, then 8, then 34, as in Figure 37.8. In this case, the scheduler should merge the requests for blocks 33 and 34 into a single two-block request; any reordering that the scheduler does is performed upon the merged requests. Merging is particularly important at the OS level, as it reduces the number of requests sent to the disk and thus lowers overheads.

One ﬁnal problem that modern schedulers address is this: how long should the system wait before issuing an I/O to disk? One might naively think that the disk, once it has even a single I/O, should immediately issue the request to the drive; this approach is called work-conserving, as the disk will never be idle if there are requests to serve. However, research on anticipatory disk scheduling has shown that sometimes it is better to

EASY PIECES

wait for a bit [ID01], in what is called a non-work-conserving approach. By waiting, a new and “better” request may arrive at the disk, and thus overall efﬁciency is increased. Of course, deciding when to wait, and for how long, can be tricky; see the research paper for details, or check out the Linux kernel implementation to see how such ideas are transitioned into practice (if you are the ambitious sort).

37.6 Summary

We have presented a summary of how disks work. The summary is actually a detailed functional model; it does not describe the amazing physics, electronics, and material science that goes into actual drive design. For those interested in even more details of that nature, we suggest a different major (or perhaps minor); for those that are happy with this model, good! We can now proceed to using the model to build more interesting systems on top of these incredible devices.
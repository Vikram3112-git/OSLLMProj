# Linux Commands (Operating Systems Lab)

## Files and directories
- pwd: print the current working directory.
- ls: list directory contents. ls -l (long format: permissions, links, owner, group, size, date), ls -a (include hidden files starting with .), ls -lh (human-readable sizes), ls -R (recursive).
- cd dir: change directory. cd .. (parent), cd ~ or cd (home), cd - (previous directory).
- mkdir dir: make a directory; mkdir -p a/b/c makes parent directories too. rmdir dir removes an empty directory.
- touch file: create an empty file or update its timestamp.
- cp src dst: copy; cp -r dir1 dir2 copies a directory recursively; cp -i asks before overwriting.
- mv src dst: move or rename.
- rm file: remove a file; rm -r dir removes a directory and its contents; rm -i asks first. There is no recycle bin.
- ln target link: hard link; ln -s target link: symbolic (soft) link.
- find . -name "*.c": search for files by name; locate name searches a prebuilt database.

## Viewing and processing text
- cat file: print a file; cat f1 f2 > f3 joins files. tac prints in reverse line order.
- head -n 5 file / tail -n 5 file: first or last lines; tail -f follows a growing log file.
- less file / more file: page through a file.
- wc file: count lines, words and characters (wc -l lines only).
- sort file: sort lines; sort -n numeric, sort -r reverse, sort -u unique.
- uniq: remove adjacent duplicate lines (usually after sort); uniq -c counts them.
- cut -d',' -f2 file: take field 2 of comma-separated lines.
- grep pattern file: print matching lines; grep -i (ignore case), -n (line numbers), -v (non-matching), -r (recursive), -c (count).
- tee file: copy standard input to a file and to the screen at the same time.
- diff f1 f2: show differences; cmp f1 f2: compare byte by byte.
- echo text: print text; echo $HOME prints a variable.

## Permissions
Each file has read (r = 4), write (w = 2) and execute (x = 1) permissions for the user (owner), group and others. ls -l shows them as, for example, -rwxr-xr--.
- chmod 754 file: rwx for the owner (7 = 4 + 2 + 1), r-x for the group (5 = 4 + 1), r-- for others (4).
- chmod u+x file, chmod go-w file: symbolic form (u user, g group, o others, a all; + add, - remove, = set).
- chown user:group file: change the owner and group. umask sets default permissions for new files.

## Processes
- ps: list processes; ps -ef or ps aux shows all processes with PID, parent PID, CPU and memory use.
- top (or htop): live view of processes and CPU use.
- kill PID: send SIGTERM (polite termination); kill -9 PID: send SIGKILL, which cannot be caught or ignored. killall name kills by name.
- command &: run in the background; jobs lists background jobs; fg %1 and bg %1 move job 1 to the foreground or background; Ctrl+Z suspends the foreground job; Ctrl+C sends SIGINT.
- nice -n 10 command: start with lower priority (nice values -20 highest to 19 lowest); renice changes a running process.
- pstree shows the process tree.

## Archives, disks and system information
- tar -cvf archive.tar dir (create), tar -xvf archive.tar (extract), tar -czvf archive.tar.gz dir (create compressed).
- gzip file / gunzip file.gz; zcat file.gz shows a compressed file without extracting.
- df -h: free space on file systems; du -sh dir: space used by a directory.
- mount / umount: attach or detach a file system.
- free -h: memory usage. uname -a: kernel and system information. who, whoami, w: logged-in users. date, cal: date and calendar. uptime: running time and load.
- passwd: change your password. sudo command: run as administrator. man command: the manual page; command --help: short help.
- ssh user@host: remote login; scp copies files over ssh; ping host and host name check the network.

## Pipes and redirection
- command > file: write standard output to a file (overwrite); >> appends.
- command < file: read standard input from a file.
- command 2> file: redirect error messages; command > file 2>&1 sends both output and errors to the file.
- cmd1 | cmd2: a pipe sends the output of cmd1 to the input of cmd2. Each command runs as a separate process connected by a pipe created with the pipe() system call.
Examples: ls -l | wc -l (count entries), ps aux | grep firefox (find a process), cat words.txt | tr ' ' '\n' | sort | uniq -c | sort -nr | head (most common words).

## Common mistakes
- Using rm -r without checking the path; deleted files cannot be recovered.
- Reading chmod digits in the wrong order: the first digit is the owner, then group, then others.
- Expecting kill to stop every process; a process can catch SIGTERM, but not SIGKILL.

## Viva questions
- What does chmod 640 give? rw- for the owner, r-- for the group, nothing for others.
- Difference between > and >>? > overwrites the file; >> appends to it.
- How do ps and top get their information? From the /proc file system maintained by the kernel.

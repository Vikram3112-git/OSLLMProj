"""
Build OSLLM's universal-sources database.

Downloads authoritative reference material for the Operating Systems course (BCSE303L) and
saves it as clean text (with title, URL and licence) in knowledge_base/universal/, where
ingest.py indexes it together with our own course notes and the student's own files.

  Textbooks (university-authored, freely available online)
    - Operating Systems: Three Easy Pieces (Arpaci-Dusseau, Univ. of Wisconsin-Madison):
      processes, CPU scheduling, concurrency (locks, semaphores, deadlock), memory
      (free space, paging, TLBs, swapping and replacement policy) and persistence (disks, files)
    - Operating Systems and Middleware (Hailperin, Gustavus Adolphus College; listed in the
      Open Textbook Library, CC BY-SA 3.0): Chapter 3, Scheduling
  Official documentation
    - Microsoft Learn: Windows thread scheduling (CC BY 4.0)
    - Linux man-pages: scheduling, fork/execve/wait, pthreads, semaphores, pipes, shared memory (GPL-2.0+)
    - Linux kernel documentation: CFS, EEVDF, nice levels, scheduling domains, memory concepts (GPL-2.0)
  Course material from the OSTEP authors
    - the READMEs of the OSTEP scheduling homework simulators (FIFO/SJF/RR, MLFQ, lottery,
      multiprocessor), which explain each policy with worked runs

Textbook chapters and OSTEP homework texts (files named book_*) are downloaded for personal
study on this computer only; they are not redistributed with the project.

Run:  python fetch_sources.py           (run.sh does this automatically the first time)
      python fetch_sources.py --force   (download everything again)
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

OUT = Path(__file__).resolve().parent / "knowledge_base" / "universal"
UA = {"User-Agent": "OSLLM-student-project/1.0 (educational, offline tutor; VIT Vellore)"}

OSTEP_LICENCE = "Free online textbook by the authors; downloaded for personal study, not redistributed"
OSTEP = [  # (file name, chapter title)
    ("intro", "Introduction to Operating Systems"),
    ("cpu-intro", "The Abstraction: The Process"),
    ("cpu-api", "Interlude: Process API"),
    ("cpu-mechanisms", "Mechanism: Limited Direct Execution"),
    ("cpu-sched", "Scheduling: Introduction"),
    ("cpu-sched-mlfq", "Scheduling: The Multi-Level Feedback Queue"),
    ("cpu-sched-lottery", "Scheduling: Proportional Share"),
    ("cpu-sched-multi", "Multiprocessor Scheduling (Advanced)"),
    ("vm-intro", "The Abstraction: Address Spaces"),
    ("vm-mechanism", "Mechanism: Address Translation"),
    ("vm-segmentation", "Segmentation"),
    ("vm-freespace", "Free-Space Management"),
    ("vm-paging", "Paging: Introduction"),
    ("vm-tlbs", "Paging: Faster Translations (TLBs)"),
    ("vm-smalltables", "Paging: Smaller Tables"),
    ("vm-beyondphys", "Beyond Physical Memory: Mechanisms"),
    ("vm-beyondphys-policy", "Beyond Physical Memory: Policies"),
    ("threads-intro", "Concurrency: An Introduction"),
    ("threads-locks", "Locks"),
    ("threads-cv", "Condition Variables"),
    ("threads-sema", "Semaphores"),
    ("threads-bugs", "Common Concurrency Problems (including deadlock)"),
    ("file-disks", "Hard Disk Drives (including disk scheduling)"),
    ("file-intro", "Interlude: Files and Directories"),
    ("file-implementation", "File System Implementation"),
]
OSTEP_URLS = ["https://pages.cs.wisc.edu/~remzi/OSTEP/{}.pdf", "https://pages.cs.wisc.edu/~remzi/OSFEP/{}.pdf"]

HAILPERIN_URLS = [  # newest revision first; the Open Textbook Library link redirects to the current PDF
    "https://gustavus.edu/+max/os-book/osm-rev1.3.1.pdf",
    "https://gustavus.edu/mcs/max/os-book/osm-rev1.3.1.pdf",
    "https://open.umn.edu/opentextbooks/formats/2035",
    "https://gustavus.edu/+max/os-book/osm-rev1.1.4.pdf",
    "https://gustavus.edu/academics/departments/mathematics-computer-science-and-statistics/max/os-book/free-osbook.pdf",
]

MS_BASE = "https://raw.githubusercontent.com/MicrosoftDocs/win32/docs/desktop-src/ProcThread/{}.md"
MS_PAGE = "https://learn.microsoft.com/en-us/windows/win32/procthread/{}"
MICROSOFT = ["scheduling", "scheduling-priorities", "priority-boosts", "priority-inversion",
             "context-switches", "multiple-processors", "multitasking"]

MAN_BASE = "https://raw.githubusercontent.com/mkerrisk/man-pages/master/{}"
MAN_PAGES = [  # (path in the man-pages repo, title, man7.org page)
    ("man7/sched.7", "sched(7): overview of CPU scheduling", "man7/sched.7.html"),
    ("man2/sched_rr_get_interval.2", "sched_rr_get_interval(2): the Round Robin time quantum",
     "man2/sched_rr_get_interval.2.html"),
    ("man2/sched_setaffinity.2", "sched_setaffinity(2): CPU affinity of a thread", "man2/sched_setaffinity.2.html"),
    ("man2/fork.2", "fork(2): create a child process", "man2/fork.2.html"),
    ("man2/execve.2", "execve(2): execute a program", "man2/execve.2.html"),
    ("man2/wait.2", "wait(2): wait for a process to change state", "man2/wait.2.html"),
    ("man7/pthreads.7", "pthreads(7): POSIX threads", "man7/pthreads.7.html"),
    ("man7/sem_overview.7", "sem_overview(7): POSIX semaphores", "man7/sem_overview.7.html"),
    ("man7/pipe.7", "pipe(7): pipes and FIFOs", "man7/pipe.7.html"),
    ("man7/shm_overview.7", "shm_overview(7): POSIX shared memory", "man7/shm_overview.7.html"),
]

OSTEP_HW_URL = "https://raw.githubusercontent.com/remzi-arpacidusseau/ostep-homework/master/{}/README.md"
OSTEP_HW = [  # the authors' explanations of their scheduling simulators, with worked runs
    ("cpu-sched", "Scheduling simulator: FIFO, SJF and Round Robin"),
    ("cpu-sched-mlfq", "MLFQ simulator"),
    ("cpu-sched-lottery", "Lottery scheduling simulator"),
    ("cpu-sched-multi", "Multiprocessor scheduling simulator"),
]

KERNEL_URL = "https://raw.githubusercontent.com/torvalds/linux/master/Documentation/{}.rst"
KERNEL = {  # only the documents that match the syllabus level (path under Documentation/)
    "scheduler/sched-design-CFS": "Linux CFS scheduler design",
    "scheduler/sched-eevdf": "Linux EEVDF scheduler",
    "scheduler/sched-nice-design": "Linux nice levels and scheduler design",
    "scheduler/sched-domains": "Linux scheduling domains and load balancing",
    "admin-guide/mm/concepts": "Linux memory management concepts",
}


def get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def get_first(urls: list[str], pdf: bool = False) -> tuple[bytes, str]:
    """Return the first URL that downloads (and, for pdf=True, really is a PDF)."""
    last = None
    for u in urls:
        try:
            data = get(u)
            if pdf and not data.startswith(b"%PDF"):
                raise RuntimeError(f"{u} did not return a PDF")
            return data, u
        except Exception as e:  # try the next mirror
            last = e
    raise last or RuntimeError("no URL worked")


def header(title: str, url: str, licence: str) -> str:
    return (f"# {title}\n\nSource URL: {url}\nSource: {title}\nLicence: {licence}\n"
            f"Retrieved: {date.today().isoformat()}\n\n")


def tidy(text: str) -> str:
    text = re.sub(r"[ \t]+\n", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


# ------------------------------------------------------------------ PDF textbooks
STOP_HEADINGS = re.compile(r"^(references|homework|homework \(simulation\)|homework \(measurement\)|exercises|"
                           r"programming projects|exploration projects|notes)$", re.I)
RUNNING_HEAD = re.compile(r"three easy pieces|operating systems \[version|www\.ostep\.org|arpaci-dusseau", re.I)
PAGE_MARK = re.compile(r"^\d+$|^\d+\s+[A-Z][A-Z ,:()-]+$|^[A-Z][A-Z ,:()-]+\s+\d+$")   # "12  SCHEDULING" etc.


def pdf_blocks_to_text(pdf, first: int, last: int) -> str:
    """Join PDF text blocks into paragraphs, skipping page headers/footers and stopping at
    the chapter's references / homework section."""
    paras = []
    for pno in range(first, last + 1):
        page = pdf[pno]
        h = page.rect.height
        for x0, y0, x1, y1, text, *_ in page.get_text("blocks"):
            if y1 < h * 0.07 or y0 > h * 0.93:          # running header / footer area
                continue
            t = re.sub(r"-\n(?=[a-z])", "", text)        # join hyphenated line breaks
            t = re.sub(r"\s*\n\s*", " ", t).strip()
            if not t or ((RUNNING_HEAD.search(t) or PAGE_MARK.match(t)) and len(t) < 80):
                continue
            if STOP_HEADINGS.match(re.sub(r"^[\d.]+\s*", "", t)):
                return "\n\n".join(paras)
            paras.append(t)
    return "\n\n".join(paras)


def fetch_ostep(name: str, title: str) -> str:
    from core.pdfio import pymupdf as fitz  # PyMuPDF

    data, url = get_first([u.format(name) for u in OSTEP_URLS], pdf=True)
    with fitz.open(stream=data, filetype="pdf") as pdf:
        body = pdf_blocks_to_text(pdf, 0, len(pdf) - 1)
    full = f"{title} (Operating Systems: Three Easy Pieces)"
    return header(full, url, OSTEP_LICENCE) + tidy(body)


def fetch_hailperin() -> str:
    from core.pdfio import pymupdf as fitz

    data, url = get_first(HAILPERIN_URLS, pdf=True)
    with fitz.open(stream=data, filetype="pdf") as pdf:
        start = end = None
        toc = pdf.get_toc()
        for i, (level, name, page) in enumerate(toc):
            if level == 1 and re.fullmatch(r"(\d+\s+)?Scheduling", name.strip(), re.I):
                start = page - 1
                end = next((p - 2 for lv, _, p in toc[i + 1:] if lv == 1), len(pdf) - 1)
                break
        if start is None:                            # no bookmarks: find the chapter by its text
            for pno in range(len(pdf)):
                head = pdf[pno].get_text("text")[:200]
                if start is None and re.search(r"Chapter\s+3\s+Scheduling", head, re.S):
                    start = pno
                elif start is not None and re.search(r"Chapter\s+4\b", head):
                    end = pno - 1
                    break
        if start is None:
            raise RuntimeError("could not find the Scheduling chapter")
        body = pdf_blocks_to_text(pdf, start, end if end is not None else len(pdf) - 1)
    title = "Scheduling, Chapter 3 (Hailperin, Operating Systems and Middleware)"
    return header(title, url, "CC BY-SA 3.0") + tidy(body)


# ------------------------------------------------------------------ Microsoft Learn
def clean_ms_markdown(text: str) -> str:
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)          # YAML front matter
    text = re.sub(r"</?dl>|</?dt>|</?dd>|<br\s*/?>", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)               # links -> text
    text = text.replace("\\_", "_").replace("\\*", "*")
    text = re.sub(r"^\s*-\s{2,}", "- ", text, flags=re.M)
    text = re.sub(r"(?ms)^## Related topics.*", "", text)
    return tidy(text)


def fetch_microsoft(name: str) -> str:
    raw = get(MS_BASE.format(name)).decode("utf-8", errors="ignore")
    m = re.search(r"^title:\s*(.+)$", raw, re.M)
    title = (m.group(1).strip() if m else name.replace("-", " ").title()) + " (Microsoft Learn, Windows)"
    return header(title, MS_PAGE.format(name), "CC BY 4.0") + clean_ms_markdown(raw)


# ------------------------------------------------------------------ man page
def roff_to_text(src: str) -> str:
    out = []
    for line in src.splitlines():
        if line.startswith(('.\\"', "'\\\"")) or line.startswith((".TH", ".ad", ".nh", ".in", ".nf", ".fi", ".ft")):
            continue
        m = re.match(r"^\.(SH|SS)\s+(.*)", line)
        if m:
            name = m.group(2).strip('"')
            if m.group(1) == "SH" and name.upper() in ("SEE ALSO", "COLOPHON"):
                break
            out.append(("\n## " if m.group(1) == "SH" else "\n### ") + name.title() + "\n")
            continue
        if re.match(r"^\.(PP|P|LP|TP|IP|sp|br|RS|RE)\b", line):
            out.append("")
            m = re.match(r"^\.IP\s+(\S+)", line)
            if m and m.group(1) not in ('""', "*"):
                out.append(m.group(1))
            continue
        m = re.match(r"^\.(B|I|BR|IR|RB|RI|BI|IB)\s+(.*)", line)
        if m:
            args = [a.strip('"') for a in re.findall(r'"[^"]*"|\S+', m.group(2))]
            line = " ".join(args) if m.group(1) in ("B", "I") else "".join(args)   # .BR etc. alternate fonts, no spaces
        elif line.startswith("."):
            continue
        out.append(line)
    text = "\n".join(out)
    text = re.sub(r"\\f[BIRP]|\\f\(..|\\&|\\:", "", text)
    text = text.replace("\\-", "-").replace("\\(em", "-").replace("\\(en", "-").replace("\\e", "\\")
    text = text.replace('\\(dq', '"').replace("\\(aq", "'")
    paras = [re.sub(r"\s*\n\s*", " ", p).strip() if not p.lstrip().startswith("#") else p.strip()
             for p in re.split(r"\n\s*\n", text)]
    return tidy("\n\n".join(p for p in paras if p))


def fetch_man(path: str, title: str, page: str) -> str:
    raw = get(MAN_BASE.format(path)).decode("utf-8", errors="ignore")
    return header(f"{title} (Linux man-pages)", f"https://man7.org/linux/man-pages/{page}", "GPL-2.0+") + roff_to_text(raw)


def fetch_ostep_hw(folder: str, title: str) -> str:
    raw = get(OSTEP_HW_URL.format(folder)).decode("utf-8", errors="ignore")
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", raw)
    return header(f"{title} (OSTEP homework)", f"https://github.com/remzi-arpacidusseau/ostep-homework/tree/master/{folder}",
                  OSTEP_LICENCE) + tidy(text)


# ------------------------------------------------------------------ kernel docs
def clean_rst(text: str) -> str:
    lines, out, i = text.splitlines(), [], 0
    while i < len(lines):
        line = lines[i]
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if line.startswith(".. ") or line.startswith("SPDX"):
            i += 1
            continue
        if re.fullmatch(r"[=\-~^*#]{3,}", line.strip()):
            i += 1
            continue
        if line.strip() and re.fullmatch(r"[=\-~^*#]{3,}", nxt.strip()) and len(nxt.strip()) >= len(line.strip()) - 2:
            out.append("\n## " + line.strip() + "\n")
            i += 2
            continue
        out.append(line.rstrip())
        i += 1
    text = "\n".join(out)
    text = re.sub(r"``(.*?)``", r"\1", text)
    text = re.sub(r":\w+:`([^`]*)`", r"\1", text)
    return tidy(text)


def fetch_kernel(name: str, title: str) -> str:
    raw = get(KERNEL_URL.format(name)).decode("utf-8", errors="ignore")
    return header(title + " (Linux kernel documentation)", f"https://docs.kernel.org/{name}.html",
                  "GPL-2.0") + clean_rst(raw)


# ------------------------------------------------------------------ main
def jobs():
    for name, title in OSTEP:
        yield f"book_ostep_{name.replace('-', '_')}.md", lambda n=name, t=title: fetch_ostep(n, t)
    yield "book_hailperin_ch3_scheduling.md", fetch_hailperin
    for name in MICROSOFT:
        yield f"ms_{name.replace('-', '_')}.md", lambda n=name: fetch_microsoft(n)
    for path, title, page in MAN_PAGES:
        name = path.split("/")[1].replace(".", "_")
        yield f"man_{name}.md", lambda p=path, t=title, g=page: fetch_man(p, t, g)
    for folder, title in OSTEP_HW:
        yield f"book_ostep_hw_{folder.replace('-', '_')}.md", lambda f=folder, t=title: fetch_ostep_hw(f, t)
    for name, title in KERNEL.items():
        yield f"kernel_{name.split('/')[-1].lower().replace('-', '_')}.md", lambda n=name, t=title: fetch_kernel(n, t)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--force", action="store_true", help="download again even if files exist")
    args = p.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    wanted = set()
    saved, failed = 0, []
    for fname, fetch in jobs():
        wanted.add(fname)
        path = OUT / fname
        if path.exists() and not args.force:
            saved += 1
            continue
        try:
            text = fetch()
            path.write_text(text, encoding="utf-8")
            saved += 1
            print(f"  saved  {fname:42s} ({len(text.split()):,} words)")
        except Exception as e:  # network problems: keep going with the rest
            failed.append(f"{fname} ({e.__class__.__name__}{': ' + str(getattr(e, 'code', '')) if getattr(e, 'code', None) else ''})")
    for old in OUT.glob("*.md"):            # remove sources we no longer use
        if old.name not in wanted:
            old.unlink()
            print(f"  removed {old.name} (no longer in the source list)")
    print(f"\nUniversal sources: {saved} documents in {OUT}")
    if failed:
        print("Could not download: " + "; ".join(failed))
        print("OSLLM still works with what was saved. Run this again when you are online.")
    return 0 if saved else 1


if __name__ == "__main__":
    sys.exit(main())

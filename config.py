"""Central configuration. Override any value with an environment variable."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_DIR = Path(os.getenv("PSLLM_KNOWLEDGE_DIR", BASE_DIR / "knowledge_base"))
DATA_DIR = Path(os.getenv("PSLLM_DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ---- LLM (instruction-tuned, served locally by Ollama) -------------------
# Recommended in the reference doc: Qwen 3 / Llama 3.x / Mistral Small / Gemma 3.
# "osllm" is built from the Modelfile on top of qwen3:8b (run.sh does this automatically).
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LLM_MODEL = os.getenv("PSLLM_MODEL", "osllm")
LLM_CONTEXT = int(os.getenv("PSLLM_NUM_CTX", "4096"))     # smaller context reduces prompt processing time
LLM_KEEP_ALIVE = os.getenv("PSLLM_KEEP_ALIVE", "60m")     # keep the model loaded between questions
LLM_TIMEOUT = int(os.getenv("PSLLM_TIMEOUT", "300"))
LLM_NUM_PREDICT = int(os.getenv("PSLLM_NUM_PREDICT", "1400"))  # allow complete, exam-ready explanations

# ---- RAG ------------------------------------------------------------------
# BGE embeddings, as specified. Use "BAAI/bge-base-en-v1.5" on low-RAM machines.
EMBEDDING_MODEL = os.getenv("PSLLM_EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
CHUNK_SIZE = 900          # characters
CHUNK_OVERLAP = 150       # characters
TOP_K = 6
MAX_UNIVERSAL = 4         # at most this many universal-source passages per answer
COURSE_NOTES_BONUS = 0.03 # small preference for our syllabus-aligned notes
TEXTBOOK_BONUS = 0.015    # textbook chapters rank above reference documentation
MY_FILES_DIR = KNOWLEDGE_DIR / "my_files"     # PDFs / notes the student adds in the app
MAX_UPLOAD_MB = 40
INDEX_PATH = DATA_DIR / "faiss.index"
CHUNKS_PATH = DATA_DIR / "chunks.json"

# ---- Student profile ------------------------------------------------------
DB_PATH = DATA_DIR / "student_profile.db"

# ---- Learning model -------------------------------------------------------
# The BCSE303L Operating Systems syllabus, unit by unit (the Learn page groups topics this way)
UNITS = [
    ("Introduction & OS Structure", ["OS Introduction & Structure", "System Calls & Interrupts"]),
    ("Processes & Threads", ["Processes & Process Operations", "Threads & Multithreading", "Inter-process Communication"]),
    ("CPU Scheduling", ["Scheduling Fundamentals", "Scheduling Criteria", "FCFS", "SJF", "SRTF",
                        "Priority Scheduling", "Round Robin", "Multilevel Queue & Feedback Queue",
                        "Multiprocessor & Real-Time Scheduling"]),
    ("Process Synchronization", ["Critical Section & Peterson's Solution", "Mutex Locks & Semaphores",
                                 "Classical Synchronization Problems"]),
    ("Deadlocks", ["Deadlock Characterization", "Deadlock Prevention & Avoidance (Banker's)",
                   "Deadlock Detection & Recovery"]),
    ("Memory Management", ["Memory Management Basics", "Contiguous Memory Allocation", "Paging & Segmentation"]),
    ("Virtual Memory", ["Demand Paging", "Page Replacement", "Thrashing & Working Set"]),
    ("Storage & File Systems", ["File Systems", "Disk Scheduling"]),
    ("Linux", ["Linux Commands"]),
]
TOPICS = [t for _, topics in UNITS for t in topics]
UNIT_OF = {t: u for u, topics in UNITS for t in topics}

# Topics with exactly solved numericals, and the algorithms each one uses.
# CPU scheduling uses core/scheduler_engine.py; the others use core/os_solvers.py.
NUMERICAL_TOPICS = {
    "FCFS": ["FCFS"],
    "SJF": ["SJF"],
    "SRTF": ["SRTF"],
    "Priority Scheduling": ["PRIORITY_NP", "PRIORITY_P"],
    "Round Robin": ["RR"],
    "Deadlock Prevention & Avoidance (Banker's)": ["BANKERS", "REQUEST"],
    "Deadlock Detection & Recovery": ["DETECT"],
    "Contiguous Memory Allocation": ["FIRST", "BEST", "WORST", "NEXT"],
    "Page Replacement": ["FIFO", "LRU", "OPT"],
    "Disk Scheduling": ["D_FCFS", "SSTF", "SCAN", "C-SCAN", "LOOK", "C-LOOK"],
}
CPU_ALGOS = {"FCFS", "SJF", "SRTF", "PRIORITY_NP", "PRIORITY_P", "RR"}

DIFFICULTIES = ["easy", "medium", "hard"]
MASTERY_ALPHA = 0.35        # weight of the newest score in the mastery average
MASTERED_AT = 0.80          # mastery needed to move on ...
MIN_ATTEMPTS_TO_MASTER = 3  # ... after at least this many practice attempts
RELEARN_BELOW = 0.40        # mastery below this ...
RELEARN_AFTER_ATTEMPTS = 3  # ... after this many attempts since the last lesson triggers re-learning
HINT_PENALTY = 0.15         # score reduction per hint used

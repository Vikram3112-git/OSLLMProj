#!/usr/bin/env bash
# Cross-platform (Linux/macOS) OSLLM launcher. Windows users: run run.bat.
set -Eeuo pipefail
cd "$(dirname "$0")"

say() { printf '\n\033[1;36m==> %s\033[0m\n' "$1"; }
fail() { echo "ERROR: $*" >&2; exit 1; }

MODE="${1:-}"; [[ -n "$MODE" ]] && shift || true
case "$MODE" in fast) BASE_MODEL="${OSLLM_BASE:-qwen3:4b}";; quality) BASE_MODEL="${OSLLM_BASE:-qwen3:8b}";; *) BASE_MODEL="${OSLLM_BASE:-}";; esac

# Detect RAM portably. Defaults conservatively to the smaller model if unknown.
if [[ -z "$BASE_MODEL" ]]; then
  RAM_GB=8
  if [[ "$(uname -s)" == "Darwin" ]]; then
    BYTES=$(sysctl -n hw.memsize 2>/dev/null || echo 0)
    [[ "$BYTES" =~ ^[0-9]+$ ]] && RAM_GB=$((BYTES / 1024 / 1024 / 1024))
  elif [[ -r /proc/meminfo ]]; then
    RAM_GB=$(awk '/MemTotal/ {printf "%d", $2/1024/1024}' /proc/meminfo)
  fi
  if (( RAM_GB >= 12 )); then BASE_MODEL=qwen3:8b; else BASE_MODEL=qwen3:4b; fi
fi

# Python: prefer python3, with a clear version check.
PYTHON="${PYTHON:-}"
if [[ -z "$PYTHON" ]]; then
  for p in python3 python; do
    if command -v "$p" >/dev/null 2>&1 && "$p" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then PYTHON="$p"; break; fi
  done
fi
[[ -n "$PYTHON" ]] || fail "Python 3.10+ is required. Install Python from https://www.python.org/downloads/ and run this script again."

# Ollama is installed separately on macOS; Linux installer can install it if possible.
if ! command -v ollama >/dev/null 2>&1; then
  if [[ "$(uname -s)" == "Darwin" ]]; then
    fail "Ollama is missing. Install it from https://ollama.com/download/mac, open it once, then rerun ./run.sh."
  elif command -v curl >/dev/null 2>&1; then
    say "Installing Ollama (internet access required)"
    curl -fsSL https://ollama.com/install.sh | sh || fail "Ollama installation failed. Install it from https://ollama.com/download and retry."
  else
    fail "Ollama and curl are required. Install Ollama from https://ollama.com/download and retry."
  fi
fi

if ! ollama list >/dev/null 2>&1; then
  if [[ "$(uname -s)" == "Darwin" ]]; then
    open -a Ollama >/dev/null 2>&1 || true
  else
    (nohup ollama serve >/dev/null 2>&1 &) || true
  fi
  for _ in $(seq 1 30); do ollama list >/dev/null 2>&1 && break; sleep 1; done
fi
ollama list >/dev/null 2>&1 || fail "Ollama is installed but not running. Start Ollama, then rerun ./run.sh."

if ! ollama list | awk '{print $1}' | grep -Fxq "$BASE_MODEL"; then
  say "Downloading $BASE_MODEL (first run only; several GB)"
  ollama pull "$BASE_MODEL" || fail "Could not download model. Check internet/disk space and run ./run.sh again."
fi
sed "s|^FROM .*|FROM ${BASE_MODEL}|" Modelfile > data.Modelfile.active
ollama create osllm -f data.Modelfile.active >/dev/null || fail "Could not create OSLLM model. Check Ollama and available disk space."
rm -f data.Modelfile.active
export PSLLM_MODEL="${PSLLM_MODEL:-osllm}"

if [[ ! -d venv ]]; then say "Creating Python environment"; "$PYTHON" -m venv venv || fail "Could not create venv. On Ubuntu/Debian install python3-venv."; fi
source venv/bin/activate
if [[ ! -f venv/.installed || requirements.txt -nt venv/.installed ]]; then
  say "Installing Python dependencies (first run only)"
  python -m pip install --upgrade pip || fail "Could not upgrade pip."
  if [[ "$(uname -s)" == "Linux" ]]; then
    python -m pip install torch --index-url https://download.pytorch.org/whl/cpu || fail "Could not install PyTorch."
  else
    python -m pip install torch || fail "Could not install PyTorch."
  fi
  python -m pip install -r requirements.txt || fail "Could not install requirements. Check Python version and internet access."
  touch venv/.installed
fi

SOURCES_VERSION=2
if [[ "$MODE" == sources || ! -d knowledge_base/universal || -z "$(ls -A knowledge_base/universal 2>/dev/null | grep 'book_' || true)" || "$(cat knowledge_base/universal/.version 2>/dev/null || true)" != "$SOURCES_VERSION" ]]; then
  say "Downloading course reference sources (first run only)"
  python fetch_sources.py || echo "WARNING: some sources failed to download; continuing with available sources."
  echo "$SOURCES_VERSION" > knowledge_base/universal/.version
fi
mkdir -p knowledge_base/my_files
if [[ "$MODE" == ingest || "$MODE" == sources || ! -f data/faiss.index || $(find knowledge_base -type f -newer data/faiss.index -print -quit 2>/dev/null) ]]; then
  say "Building the search index (first run downloads an embedding model)"
  python ingest.py || fail "Knowledge indexing failed. Review the error above and rerun ./run.sh."
fi
[[ "$MODE" == ingest || "$MODE" == sources ]] && exit 0

case "$MODE" in
  dataset) python finetune/verify_engine.py --n 5000 && python finetune/verify_solvers.py && python finetune/build_dataset.py; exit $? ;;
  eval) python finetune/eval_model.py --model "${2:-${PSLLM_MODEL:-osllm}}" --n "${3:-60}"; exit $? ;;
  test) python test_osllm.py "$@"; exit $? ;;
esac
say "Starting OSLLM at http://localhost:8501 (Ctrl+C to stop)"
if [[ "$(uname -s)" == Darwin ]]; then (sleep 2; open http://localhost:8501 >/dev/null 2>&1 || true) &
elif command -v xdg-open >/dev/null 2>&1; then (sleep 2; xdg-open http://localhost:8501 >/dev/null 2>&1 || true) & fi
python server.py

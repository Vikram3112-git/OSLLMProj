# OSLLM — cross-platform setup guide

This package supports **Windows 10/11, macOS, and Linux**. OSLLM runs a local Ollama model and a Python web application. It does not need an API key or paid AI API. The first setup requires internet access and several GB of free disk space; later launches reuse downloaded packages, the model, and the search index.

## Before starting

1. Download and extract the complete ZIP to a normal folder (not inside the ZIP preview, OneDrive-synced folder, or a read-only directory). Keep the `OSLLM` folder together.
2. Install **Python 3.10 or newer**:
   - Windows: https://www.python.org/downloads/windows/ — during installation, enable **Add Python to PATH**.
   - macOS: https://www.python.org/downloads/macos/ (or `brew install python` if Homebrew is already installed).
   - Linux: install Python 3, pip and venv from your distribution's package manager.
3. Install **Ollama** for your OS: https://ollama.com/download. Open/start Ollama once before launching OSLLM. On Linux the launcher attempts the official Ollama install script if it is missing; on Windows/macOS install it manually.
4. Keep an internet connection for first launch. The launcher downloads a model and the text-embedding model used to search the course notes. The AI model alone is several GB; allow extra space for Python packages and indexes.

## Start the application

### Windows 10/11

1. Open the extracted `OSLLM` folder in File Explorer.
2. Double-click `run.bat`. If Windows blocks scripts, right-click `run.bat` and choose **Open**, or open PowerShell in this folder and run ` .\run.bat `.
3. To use the lighter/faster model, run ` .\run.bat fast ` from PowerShell. To prefer answer quality on a capable computer, run ` .\run.bat quality `.
4. When the terminal says the server has started, open http://localhost:8501.

### macOS

1. Install and open Ollama from https://ollama.com/download/mac.
2. Open Terminal and type `cd ` (with a trailing space), then drag the extracted `OSLLM` folder into Terminal and press Enter.
3. Run `chmod +x run.sh` once, then `./run.sh`.
4. Optional: `./run.sh fast` for a smaller model, or `./run.sh quality` for the larger model.
5. The browser should open automatically; if not, visit http://localhost:8501.

### Linux

1. Open Terminal and `cd` into the extracted `OSLLM` folder.
2. Run `chmod +x run.sh` once, then `./run.sh`.
3. Optional: `./run.sh fast` or `./run.sh quality`.
4. If automatic Ollama installation fails, install it from https://ollama.com/download and rerun.

## Model choice and expected performance

- `fast` uses `qwen3:4b`: less RAM and generally faster, but may be less thorough on complex questions.
- `quality` uses `qwen3:8b`: usually more detailed, but needs more memory and can be slower, especially on CPU-only computers.
- Default selection chooses 8B on systems reporting at least 12 GB RAM; otherwise it chooses 4B. This is a conservative rule of thumb, not a performance guarantee. Set `OSLLM_BASE=qwen3:4b` or `OSLLM_BASE=qwen3:8b` to override on macOS/Linux, or use the `fast`/`quality` launcher option on all platforms.
- The first question can be slower while the model loads. The model is configured to remain loaded between questions, and responses stream as they are generated.

## Common tasks

- Stop the app: press `Ctrl+C` in the terminal running it.
- Start again: rerun the same launcher. Setup steps are skipped after successful completion.
- Rebuild the search index after adding files to `knowledge_base/my_files`: `./run.sh ingest` on macOS/Linux, or ` .\run.bat ingest ` in PowerShell on Windows.
- Refresh the course sources: `./run.sh sources` or ` .\run.bat sources `.
- Check browser: use `http://localhost:8501` on the same computer. This is local by default and is not exposed to other devices on the network.

## Troubleshooting

- **`ollama` not found / not running:** install Ollama, launch its desktop app (Windows/macOS), wait for it to finish starting, then retry.
- **Python not found:** install Python 3.10+ and reopen Terminal/PowerShell so PATH refreshes. Windows can use `py -3.11 --version`; macOS/Linux can use `python3 --version`.
- **Model download fails:** check internet access and disk space, then rerun the launcher. Ollama can resume/reuse downloads.
- **Dependency install fails:** use Python 3.11 (recommended) and make sure the OS is 64-bit. Some older OS versions may not have wheels for every dependency.
- **The app is slow or the computer runs out of memory:** stop it and relaunch with `fast` (`./run.sh fast` or ` .\run.bat fast `). Close other memory-heavy apps. Avoid `quality` on low-RAM systems.
- **Port 8501 is already in use:** close the other OSLLM instance before starting another one.
- **No browser opens:** manually navigate to http://localhost:8501 after the terminal reports that the server has started.
- **First launch appears stuck:** model and embedding downloads/indexing can take several minutes. Read the terminal output; do not close the terminal while it is installing or indexing.

## Privacy and requirements

Prompts are sent to the Ollama service running on the same computer; no hosted model API key is required by the default configuration. Initial setup downloads software, model weights, and reference material from their providers. The app listens on `127.0.0.1:8501` by default. Do not change the host to `0.0.0.0` on a public network unless you understand the security implications.

Cross-platform launchers are provided, but hardware, Python packaging, OS version, and network policies vary. The archive is syntax-checked; a successful launch on every possible machine cannot be guaranteed. If setup fails, keep the full terminal error and include your OS version and Python version when requesting help.

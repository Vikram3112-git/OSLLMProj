"""Connection to the local OSLLM model running in Ollama (standard library only)."""
import json
import re
import sys
import urllib.error
import urllib.request

OLLAMA = "http://localhost:11434"
MODEL = "osllm"
_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)


def check_ready(model=MODEL):
    try:
        with urllib.request.urlopen(f"{OLLAMA}/api/tags", timeout=5) as r:
            names = [m["name"].split(":")[0] for m in json.load(r).get("models", [])]
    except (urllib.error.URLError, OSError):
        sys.exit("Ollama is not running. Start everything with:  bash run.sh")
    if model.split(":")[0] not in names:
        sys.exit(f"Model '{model}' not found. Start everything with:  bash run.sh")


def ask(messages, model=MODEL, echo=True):
    """Send a conversation to the model. Streams the reply to the screen if echo=True."""
    body = json.dumps({"model": model, "messages": messages, "stream": True, "think": False}).encode()
    req = urllib.request.Request(f"{OLLAMA}/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    full, printed = "", 0
    with urllib.request.urlopen(req, timeout=900) as r:
        for line in r:
            if not line.strip():
                continue
            data = json.loads(line)
            if "error" in data:
                raise RuntimeError(data["error"])
            full += data.get("message", {}).get("content", "")
            if not echo:
                continue
            visible = _THINK.sub("", full)
            if "<think>" in visible:                       # still inside a think block
                visible = visible[: visible.index("<think>")]
            for i in range(6, 0, -1):                      # hold back a half-received tag
                if visible.endswith("<think>"[:i]):
                    visible = visible[:-i]
                    break
            visible = visible.lstrip()
            if len(visible) > printed:
                print(visible[printed:], end="", flush=True)
                printed = len(visible)
    if echo:
        print()
    return _THINK.sub("", full).strip()

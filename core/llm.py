"""Thin client for an instruction-tuned LLM served locally by Ollama."""
from __future__ import annotations

import json
import re
from typing import Iterator

import requests

import config

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


class LLMError(RuntimeError):
    pass


class LLM:
    def __init__(self, model: str = config.LLM_MODEL, host: str = config.OLLAMA_HOST):
        self.model = model
        self.host = host.rstrip("/")
        self.send_think = True          # turned off for models without a thinking mode (e.g. fine-tuned GGUF)

    # ------------------------------------------------------------------ utils
    def health(self) -> tuple[bool, str]:
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=5)
            r.raise_for_status()
            names = [m["name"] for m in r.json().get("models", [])]
        except Exception:
            return False, f"Ollama is not running at {self.host}. Start it with `ollama serve`."
        if not any(n == self.model or n.split(":")[0] == self.model for n in names):
            return False, f"Model `{self.model}` is not pulled. Run `ollama pull {self.model}`."
        return True, f"{self.model} ready"

    def _payload(self, system: str, user: str, temperature: float, stream: bool, json_mode: bool):
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": stream,
            "keep_alive": config.LLM_KEEP_ALIVE,
            "options": {"temperature": temperature, "num_ctx": config.LLM_CONTEXT,
                        "num_predict": config.LLM_NUM_PREDICT},
        }
        if self.send_think:
            payload["think"] = False
        if json_mode:
            payload["format"] = "json"
        return payload

    def warm_up(self) -> None:
        """Load the model into memory now, so the first real question does not wait for it."""
        try:
            requests.post(f"{self.host}/api/generate", json={"model": self.model, "prompt": "",
                                                              "keep_alive": config.LLM_KEEP_ALIVE}, timeout=300)
        except requests.RequestException:
            pass

    def _post(self, payload: dict, stream: bool):
        """POST to Ollama; if the model has no thinking mode, retry once without the think flag."""
        for _ in range(2):
            try:
                r = requests.post(f"{self.host}/api/chat", json=payload, stream=stream, timeout=config.LLM_TIMEOUT)
                if r.status_code == 400 and "think" in r.text.lower() and "think" in payload:
                    self.send_think = False
                    payload.pop("think")
                    continue
                r.raise_for_status()
                return r
            except requests.RequestException as e:
                raise LLMError(f"LLM request failed: {e}") from e
        raise LLMError("LLM request failed")

    # ------------------------------------------------------------------- calls
    def chat(self, system: str, user: str, temperature: float = 0.4, json_mode: bool = False) -> str:
        r = self._post(self._payload(system, user, temperature, False, json_mode), stream=False)
        text = r.json().get("message", {}).get("content", "")
        return _THINK_RE.sub("", text).strip()

    def stream(self, system: str, user: str, temperature: float = 0.5) -> Iterator[str]:
        r = self._post(self._payload(system, user, temperature, True, False), stream=True)

        def visible_chunks() -> Iterator[str]:
            # First remove explicit <think> blocks and partial tags from models that emit them.
            buffer, in_think = "", False
            for line in r.iter_lines():
                if not line:
                    continue
                buffer += json.loads(line).get("message", {}).get("content", "")
                while buffer:
                    if in_think:
                        end = buffer.find("</think>")
                        if end == -1:
                            buffer = buffer[-7:]
                            break
                        buffer, in_think = buffer[end + 8:], False
                        continue
                    start = buffer.find("<think>")
                    if start != -1:
                        if start:
                            yield buffer[:start]
                        buffer, in_think = buffer[start + 7:], True
                        continue
                    lt = buffer.rfind("<")
                    if lt != -1 and "<think>".startswith(buffer[lt:]):
                        if lt:
                            yield buffer[:lt]
                        buffer = buffer[lt:]
                    else:
                        yield buffer
                        buffer = ""
                    break
            if buffer and not in_think:
                yield buffer

        # Some small local models ignore prompt instructions and emit their private planning
        # as ordinary prose. Hold one paragraph at a time so that such text is never shown.
        # Small local models sometimes emit planning as ordinary prose rather than <think> tags.
        # Match common variants at the paragraph start, including the exact "Hmm..." style.
        meta_patterns = (
            r"^\s*(okay,?\s+)?(the user|the student|we are given a student|student['’]s question)\b",
            r"^\s*(hmm\b|but note:|but looking at the course material|important constraints|important:|"
            r"important to note|let me make sure|i should (start|write|answer)|i['’]ll (write|answer|explain|avoid)|"
            r"so the answer is|for the explanation structure|must avoid|my plan|internal reasoning|analysis:|"
            r"reasoning:|let me think|first, i need to|we need to answer|the user wants|the user asked|"
            r"i recall from (source|the source)|they['’]re probably|they are probably|the user seems|"
            r"the student seems|the course doesn['’]t cover|the course does not cover)\b",
            r"\b(the user['’]s previous messages|they seem frustrated|the student is asking|looking at the course material|"
            r"course material provided (is )?limited|the course description mentions|the instructions say|"
            r"since they are in a hurry|since they['’]re in a hurry|word count:|source \d+ says)\b",
            # Planning outlines commonly follow a paragraph like "For the explanation structure:"
            r"^\s*\d+[.)]\s*(start with|explain|detail|show calculation|mention why|for the explanation|"
            r"the answer should|i will|i'll|avoid mentioning)\b",
            r"^\s*[-•]\s*(mentioning segmentation|overcomplicating with|using terms like)\b",
        )

        def is_internal_paragraph(paragraph: str) -> bool:
            stripped = paragraph.strip()
            if not stripped:
                return False
            # Strong signals of process narration. Do not suppress normal explanations like
            # "The user process" or technical discussion of a student/process in OS.
            return any(re.search(pattern, stripped, re.I) for pattern in meta_patterns)

        pending = ""
        for piece in visible_chunks():
            pending += piece
            while True:
                match = re.search(r"\n[ \t]*\n", pending)
                if not match:
                    break
                paragraph = pending[:match.start()]
                separator = match.group(0)
                pending = pending[match.end():]
                if not is_internal_paragraph(paragraph):
                    yield paragraph + separator
        if pending and not is_internal_paragraph(pending):
            yield pending

    def chat_json(self, system: str, user: str, temperature: float = 0.5, retries: int = 2) -> dict:
        last_err = None
        for _ in range(retries + 1):
            text = self.chat(system, user, temperature, json_mode=True)
            try:
                return parse_json(text)
            except ValueError as e:
                last_err = e
        raise LLMError(f"LLM did not return valid JSON: {last_err}")


def parse_json(text: str) -> dict:
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError as e:
                raise ValueError(str(e)) from e
        raise ValueError("no JSON object found")

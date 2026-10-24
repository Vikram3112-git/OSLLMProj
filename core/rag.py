"""RAG pipeline: PyMuPDF loading, chunking, BGE embeddings, FAISS retrieval."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

import config

SUPPORTED = {".pdf", ".md", ".txt"}


@dataclass
class Chunk:
    text: str
    source: str
    page: int | None
    url: str | None = None
    origin: str = "course notes"     # "course notes" | "universal" | "your files"


# --------------------------------------------------------------------- loading
def _origin(path: Path, folder: Path) -> str:
    rel = path.relative_to(folder).parts
    if rel and rel[0] == "universal":
        return "universal"
    if path.parent == config.MY_FILES_DIR or (rel and rel[0] == config.MY_FILES_DIR.name):
        return "your files"
    return "your files" if path.suffix.lower() == ".pdf" else "course notes"


def _read_header(text: str, fallback: str):
    """Universal-source files start with 'Source:' / 'Source URL:' lines; strip them from the body."""
    name, url = fallback, None
    m = re.search(r"^Source:\s*(.+)$", text, re.M)
    if m:
        name = m.group(1).strip()
    m = re.search(r"^Source URL:\s*(\S+)$", text, re.M)
    if m:
        url = m.group(1).strip()
    body = re.sub(r"^(Source URL|Source|Licence|Retrieved):.*$\n?", "", text, flags=re.M)
    return name, url, body


def _pdf_page_text(page) -> str:
    """Text of one PDF page without the running header/footer and page number (top and bottom 7%),
    with hyphenated line breaks joined. Works for lecture slides as well as book pages."""
    h = page.rect.height
    parts = []
    for x0, y0, x1, y1, text, *_ in page.get_text("blocks"):
        if y1 < h * 0.07 or y0 > h * 0.93:
            continue
        t = re.sub(r"-\n(?=[a-z])", "", text)
        t = re.sub(r"[ \t]*\n[ \t]*", " ", t).strip()
        if len(t) <= 3 and t.replace(".", "").isdigit():
            continue
        if t:
            parts.append(t)
    return "\n\n".join(parts)


def load_file(path: Path, folder: Path = config.KNOWLEDGE_DIR) -> list[tuple]:
    """(text, source name, page, url, origin) for one file."""
    if path.suffix.lower() not in SUPPORTED:
        return []
    origin = _origin(path, folder)
    if path.suffix.lower() == ".pdf":
        from core.pdfio import pymupdf as fitz  # PyMuPDF

        out = []
        with fitz.open(path) as pdf:
            for i, page in enumerate(pdf, start=1):
                text = _pdf_page_text(page)
                if text.strip():
                    out.append((text, path.name, i, None, origin))
        return out
    raw = path.read_text(encoding="utf-8", errors="ignore")
    pretty = re.sub(r"^\d+\s*", "", path.stem.replace("_", " ")).strip().capitalize()
    pretty = re.sub(r"\b(os|ipc|cpu)\b", lambda m: m.group(1).upper(), pretty, flags=re.I)
    name, url, body = _read_header(raw, pretty)
    if origin == "your files":
        name = path.name          # the My files page matches passages to files by file name
    return [(body, name, None, url, origin)]


def load_documents(folder: Path):
    """Return (text, source name, page, url, origin) for every page / file in the knowledge base."""
    docs = []
    for path in sorted(folder.rglob("*")):
        docs += load_file(path, folder)
    return docs


def split_text(text: str, size: int = config.CHUNK_SIZE, overlap: int = config.CHUNK_OVERLAP) -> list[str]:
    """Paragraph-aware splitter with character overlap."""
    paragraphs = [p.strip() for p in text.replace("\r", "").split("\n\n") if p.strip()]
    chunks, current = [], ""
    for para in paragraphs:
        while len(para) > size:                      # very long paragraph
            if current:
                chunks.append(current)
                current = ""
            chunks.append(para[:size])
            para = para[size - overlap :]
        if len(current) + len(para) + 2 <= size:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current)
            tail = current[-overlap:] if current else ""
            current = f"{tail}\n\n{para}" if tail else para
    if current:
        chunks.append(current)
    return chunks


# ------------------------------------------------------------------ embeddings
_model = None


def embedder():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(config.EMBEDDING_MODEL)
    return _model


def embed(texts: list[str], is_query: bool = False) -> np.ndarray:
    if is_query and "bge" in config.EMBEDDING_MODEL.lower():
        texts = [config.BGE_QUERY_PREFIX + t for t in texts]
    if "e5" in config.EMBEDDING_MODEL.lower():
        texts = [("query: " if is_query else "passage: ") + t for t in texts]
    vecs = embedder().encode(texts, normalize_embeddings=True, show_progress_bar=not is_query)
    return np.asarray(vecs, dtype="float32")


# ----------------------------------------------------------------------- index
def _chunks_of(docs) -> list[Chunk]:
    chunks = []
    for text, source, page, url, origin in docs:
        for piece in split_text(text):
            if len(piece.strip()) >= 60:          # skip stray headings / fragments
                chunks.append(Chunk(piece, source, page, url, origin))
    return chunks


def _save(index, chunks: list[Chunk]):
    import faiss

    # write to temporary files and swap them in, so a reader never sees a half-written index
    tmp_index = config.INDEX_PATH.with_suffix(".tmp")
    tmp_chunks = config.CHUNKS_PATH.with_suffix(".tmp")
    faiss.write_index(index, str(tmp_index))
    tmp_chunks.write_text(json.dumps([c.__dict__ for c in chunks], ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp_chunks, config.CHUNKS_PATH)
    os.replace(tmp_index, config.INDEX_PATH)


def read_chunks() -> list[dict]:
    """The stored chunks as dicts, or [] if the index is missing or being replaced."""
    try:
        return json.loads(config.CHUNKS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def build_index(folder: Path = config.KNOWLEDGE_DIR) -> int:
    import faiss

    chunks = _chunks_of(load_documents(folder))
    if not chunks:
        raise RuntimeError(f"No documents found in {folder}")
    vectors = embed([c.text for c in chunks])
    index = faiss.IndexFlatIP(vectors.shape[1])   # cosine similarity (normalized)
    index.add(vectors)
    _save(index, chunks)
    return len(chunks)


def add_files(paths: list[Path], folder: Path = config.KNOWLEDGE_DIR) -> int:
    """Add new files to the existing index without re-embedding everything (used for uploads)."""
    import faiss

    if not config.INDEX_PATH.exists():
        return build_index(folder)
    index = faiss.read_index(str(config.INDEX_PATH))
    chunks = [Chunk(**c) for c in json.loads(config.CHUNKS_PATH.read_text(encoding="utf-8"))]
    names = {p.name for p in paths}
    keep = [c for c in chunks if c.source not in names]
    if len(keep) != len(chunks):                 # a file with this name was indexed before: start clean
        return build_index(folder)
    new = _chunks_of([d for p in paths for d in load_file(p, folder)])
    if new:
        index.add(embed([c.text for c in new]))
        _save(index, chunks + new)
    return len(new)


class Retriever:
    def __init__(self):
        import faiss

        if not config.INDEX_PATH.exists():
            raise FileNotFoundError("Knowledge base not indexed. Run `python ingest.py` first.")
        self.index = faiss.read_index(str(config.INDEX_PATH))
        self.chunks = [Chunk(**c) for c in json.loads(config.CHUNKS_PATH.read_text(encoding="utf-8"))]

    def retrieve(self, query: str, k: int = config.TOP_K, max_universal: int | None = None) -> list[Chunk]:
        """Retrieve from course notes and universal references.

        Always reserve part of the context for the indexed universal OS corpus, so an unrelated
        or incomplete course-note match cannot crowd out relevant textbook/reference passages.
        The returned list is ordered by similarity, with a small preference for course-specific
        material when scores are close.
        """
        if not self.chunks:
            return []
        # The flat FAISS index is small enough to score all indexed chunks; this avoids missing
        # universal references just because many course-note chunks occupy the initial top results.
        scores, ids = self.index.search(embed([query], is_query=True), len(self.chunks))
        course_ranked, universal_ranked = [], []
        for score, i in zip(scores[0], ids[0]):
            if i == -1:
                continue
            c = self.chunks[i]
            sim = float(score)
            if c.origin == "universal":
                bonus = config.TEXTBOOK_BONUS if re.search(r"Three Easy Pieces|Hailperin", c.source) else 0.0
                universal_ranked.append((sim + bonus, c))
            else:
                course_ranked.append((sim + config.COURSE_NOTES_BONUS, c))

        def diverse(items, limit):
            picked, per_source = [], {}
            for score, chunk in items:
                if per_source.get(chunk.source, 0) >= 2:
                    continue
                picked.append((score, chunk))
                per_source[chunk.source] = per_source.get(chunk.source, 0) + 1
                if len(picked) >= limit:
                    break
            return picked

        universal_limit = config.MAX_UNIVERSAL if max_universal is None else max_universal
        # Course notes remain represented, but universal sources are guaranteed a fair share.
        course_limit = max(0, k - min(universal_limit, max(1, k - 1)))
        chosen = diverse(course_ranked, course_limit) + diverse(universal_ranked, min(universal_limit, k))
        seen = {(c.source, c.page, c.text[:80]) for _, c in chosen}
        for score, chunk in sorted(course_ranked + universal_ranked, key=lambda x: x[0], reverse=True):
            key = (chunk.source, chunk.page, chunk.text[:80])
            if key in seen:
                continue
            if len(chosen) >= k:
                break
            if sum(1 for _, c in chosen if c.source == chunk.source) >= 2:
                continue
            chosen.append((score, chunk))
            seen.add(key)
        chosen.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in chosen[:k]]

    @staticmethod
    def format_context(chunks: list[Chunk]) -> str:
        parts = []
        for i, c in enumerate(chunks, 1):
            where = f"{c.source}" + (f", p.{c.page}" if c.page else "") + (
                " - universal source" if c.origin == "universal" else "")
            parts.append(f"[Source {i}: {where}]\n{c.text}")
        return "\n\n".join(parts)

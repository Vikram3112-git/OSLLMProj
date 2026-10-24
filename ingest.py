"""Build the Process Scheduling knowledge base (FAISS index).

Put PDFs / notes / question papers in knowledge_base/ and run:
    python ingest.py
"""
import config
from core.rag import build_index

if __name__ == "__main__":
    print(f"Indexing documents in {config.KNOWLEDGE_DIR} with {config.EMBEDDING_MODEL} ...")
    n = build_index()
    print(f"Done. {n} chunks stored in {config.INDEX_PATH.name}")

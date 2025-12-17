from __future__ import annotations
import hashlib, re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import chromadb
from chromadb.config import Settings

from .ollama_client import Ollama, OllamaConfig

@dataclass(frozen=True)
class RagConfig:
    persist_dir: Path
    embed_model: str = "nomic-embed-text"
    llm_model: str = "qwen2.5:7b-instruct"
    ollama_base_url: str = "http://127.0.0.1:11434"

def stable_doc_id(key: str) -> str:
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return f"doc_{h}"

def clean_text(t: str) -> str:
    t = t.replace("\r\n", "\n")
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()

def chunk_for_rag(text: str, max_chars: int = 1200, overlap: int = 150) -> List[str]:
    text = clean_text(text)
    if not text:
        return []
    out: List[str] = []
    i = 0
    n = len(text)
    while i < n:
        j = min(n, i + max_chars)
        ch = text[i:j].strip()
        if ch:
            out.append(ch)
        i = max(i + max_chars - overlap, j)
    return out

class RagIndex:
    def __init__(self, cfg: RagConfig):
        self.cfg = cfg
        self.cfg.persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=str(self.cfg.persist_dir),
            settings=Settings(anonymized_telemetry=False),
        )
        self.ollama = Ollama(OllamaConfig(base_url=self.cfg.ollama_base_url))

    def _col(self, doc_id: str):
        return self.client.get_or_create_collection(name=doc_id)

    def ingest_pages(self, doc_id: str, pages: List[str], *, field: str = "translated") -> Dict[str, int]:
        col = self._col(doc_id)

        ids: List[str] = []
        docs: List[str] = []
        metas: List[Dict[str, object]] = []
        embs: List[List[float]] = []

        chunks = 0
        for page, txt in enumerate(pages, start=1):
            txt = clean_text(txt)
            if not txt:
                continue
            for ci, ch in enumerate(chunk_for_rag(txt), start=1):
                ids.append(f"{doc_id}_{field}_p{page}_c{ci}")
                docs.append(ch)
                metas.append({"page": page, "field": field})
                chunks += 1

        for d in docs:
            embs.append(self.ollama.embeddings(self.cfg.embed_model, d))

        col.upsert(ids=ids, documents=docs, embeddings=embs, metadatas=metas)
        return {"pages_indexed": len(pages), "chunks_indexed": chunks}

    def retrieve(self, doc_id: str, query: str, k: int = 5) -> List[Tuple[int, str]]:
        col = self._col(doc_id)
        qemb = self.ollama.embeddings(self.cfg.embed_model, query)
        res = col.query(query_embeddings=[qemb], n_results=k, include=["documents", "metadatas"])
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        out: List[Tuple[int, str]] = []
        for d, m in zip(docs, metas):
            out.append((int((m or {}).get("page", 0)), d))
        return out

    def answer(self, doc_id: str, question: str, k: int = 5) -> Dict[str, object]:
        ctx = self.retrieve(doc_id, question, k=k)
        if not ctx:
            return {"answer": "I couldn't find relevant passages in the document.", "citations": []}

        excerpts = []
        citations = []
        for page, txt in ctx:
            tag = f"[p.{page}]"
            excerpts.append(f"{tag} {txt}")
            citations.append({"page": page})

        prompt = (
            "You are a helpful tutor. Answer using ONLY the excerpts. "
            "If excerpts do not contain the answer, say so. "
            "Always cite pages like [p.12].\n\n"
            "EXCERPTS:\n" + "\n\n".join(excerpts) +
            "\n\nQUESTION:\n" + question +
            "\n\nANSWER:\n"
        )
        ans = self.ollama.generate(self.cfg.llm_model, prompt)
        return {"answer": ans.strip(), "citations": citations}

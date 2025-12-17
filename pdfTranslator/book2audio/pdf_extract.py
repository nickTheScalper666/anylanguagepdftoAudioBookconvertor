from __future__ import annotations
from pathlib import Path
from typing import List
import re
import fitz  # PyMuPDF

def extract_text_by_page(pdf_path: Path) -> List[str]:
    doc = fitz.open(pdf_path)
    pages: List[str] = []
    for i in range(doc.page_count):
        page = doc.load_page(i)
        pages.append(page.get_text("text", sort=True) or "")
    doc.close()
    return pages

def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"-\n([a-z])", r"\1", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def chunk_text(text: str, max_chars: int = 1800) -> List[str]:
    text = re.sub(r"[ \t]+", " ", text).strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]
    sents = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    cur = ""
    for s in sents:
        if not s:
            continue
        if len(cur) + len(s) + 1 <= max_chars:
            cur = (cur + " " + s).strip()
        else:
            if cur:
                chunks.append(cur)
            cur = s
    if cur:
        chunks.append(cur)

    out = []
    for c in chunks:
        if len(c) <= max_chars:
            out.append(c)
        else:
            for i in range(0, len(c), max_chars):
                out.append(c[i:i+max_chars])
    return out

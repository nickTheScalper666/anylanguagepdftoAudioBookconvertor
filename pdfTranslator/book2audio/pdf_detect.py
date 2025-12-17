from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import fitz  # PyMuPDF

@dataclass(frozen=True)
class DetectReport:
    pdf_kind: str  # TEXT | SCANNED | HYBRID
    pages_total: int
    sample_pages: int
    sample_pages_with_text: int
    sample_pages_scanned_like: int
    sample_pages_with_images: int
    sampled_text_chars: int

def detect_pdf_kind(pdf_path: Path, sample_pages: int = 12) -> DetectReport:
    doc = fitz.open(pdf_path)
    total = doc.page_count
    n = min(sample_pages, total)
    pages_with_text = scanned_like = pages_with_images = text_chars = 0

    TEXT_MIN_CHARS = 140

    for i in range(n):
        page = doc.load_page(i)
        txt = (page.get_text("text") or "").strip()
        c = len(txt)
        text_chars += c
        if c >= TEXT_MIN_CHARS:
            pages_with_text += 1

        imgs = page.get_images(full=True) or []
        if imgs:
            pages_with_images += 1

        if c < 50 and imgs:
            scanned_like += 1

    doc.close()

    if n == 0:
        kind = "TEXT"
    elif pages_with_text >= int(0.75 * n):
        kind = "TEXT"
    elif scanned_like >= int(0.6 * n):
        kind = "SCANNED"
    else:
        kind = "HYBRID"

    return DetectReport(
        pdf_kind=kind,
        pages_total=total,
        sample_pages=n,
        sample_pages_with_text=pages_with_text,
        sample_pages_scanned_like=scanned_like,
        sample_pages_with_images=pages_with_images,
        sampled_text_chars=text_chars,
    )

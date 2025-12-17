from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os
from .util import have_cmd, run_cmd

@dataclass(frozen=True)
class OcrOptions:
    mode: str = "auto"     # auto|never|force
    lang: str = "eng"
    jobs: int = max(1, os.cpu_count() or 1)

def ocr_pdf_if_needed(pdf_path: Path, out_pdf: Path, detected_kind: str, opts: OcrOptions) -> Path:
    if opts.mode == "never":
        return pdf_path
    if not have_cmd("ocrmypdf"):
        return pdf_path
    if opts.mode == "auto" and detected_kind == "TEXT":
        return pdf_path

    if opts.mode == "force":
        mode = "scanned"
    else:
        mode = "hybrid" if detected_kind == "HYBRID" else "scanned"

    cmd = [
        "ocrmypdf",
        "-l", opts.lang,
        "--deskew",
        "--rotate-pages",
        "--clean",
        "--optimize", "1",
        "--jobs", str(opts.jobs),
    ]
    cmd += ["--skip-text"] if mode == "hybrid" else ["--force-ocr"]
    cmd += [str(pdf_path), str(out_pdf)]
    run_cmd(cmd)
    return out_pdf

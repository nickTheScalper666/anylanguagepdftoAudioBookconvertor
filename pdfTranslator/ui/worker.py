from __future__ import annotations

import json
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict

from PySide6.QtCore import QObject, Signal

from book2audio.pdf_detect import detect_pdf_kind
from book2audio.ocr import OcrOptions, ocr_pdf_if_needed
from book2audio.pdf_extract import extract_text_by_page, clean_text, chunk_text
from book2audio.translate_nllb import NllbTranslator, NllbConfig
from book2audio.tts_piper import TtsOptions, synthesize_wav, concat_wavs, encode_audio
from book2audio.util import have_cmd
from book2audio.rag import RagIndex, RagConfig, stable_doc_id

try:
    from langdetect import detect as langdetect_detect
except Exception:
    langdetect_detect = None  # type: ignore


@dataclass(frozen=True)
class UiConvertConfig:
    pdf_path: Path
    out_dir: Path
    voice_model: Path
    src_lang: Optional[str]
    target_lang: str
    ocr_mode: str
    ocr_lang: str
    max_chars: int
    nllb_model: str
    use_mps: bool
    audio_fmt: str
    audio_bitrate: str


def _guess_src_lang_basic(pages: List[str]) -> Optional[str]:
    if not langdetect_detect:
        return None
    sample = " ".join([clean_text(p) for p in pages[:5] if p.strip()])[:5000]
    if not sample.strip():
        return None
    iso = langdetect_detect(sample)
    mapping = {
        "en": "eng_Latn",
        "es": "spa_Latn",
        "fr": "fra_Latn",
        "de": "deu_Latn",
        "pt": "por_Latn",
        "it": "ita_Latn",
        "nl": "nld_Latn",
        "ru": "rus_Cyrl",
        "hi": "hin_Deva",
        "ja": "jpn_Jpan",
        "ko": "kor_Hang",
        "ar": "arb_Arab",
    }
    return mapping.get(iso)


class ConvertWorker(QObject):
    log = Signal(str)
    progress = Signal(int)          # 0..100 (best-effort)
    done = Signal(dict)
    error = Signal(str)

    def __init__(self, cfg: UiConvertConfig) -> None:
        super().__init__()
        self.cfg = cfg

    def run(self) -> None:
        try:
            self._run_impl()
        except Exception as e:
            self.error.emit(str(e))

    def _run_impl(self) -> None:
        cfg = self.cfg

        if not have_cmd("ffmpeg"):
            raise RuntimeError("ffmpeg not found. Install: brew install ffmpeg")
        if cfg.ocr_mode != "never" and not have_cmd("ocrmypdf"):
            self.log.emit("Warning: ocrmypdf not found (TEXT PDFs still work). Install: brew install ocrmypdf")
        if not cfg.voice_model.exists():
            raise FileNotFoundError(f"Piper voice model not found: {cfg.voice_model}")

        cfg.out_dir.mkdir(parents=True, exist_ok=True)
        job_id = uuid.uuid4().hex[:12]
        job_dir = cfg.out_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        self.log.emit("Detecting PDF type…")
        det = detect_pdf_kind(cfg.pdf_path)
        (job_dir / "detect.json").write_text(json.dumps(det.__dict__, indent=2), encoding="utf-8")
        self.log.emit(f"Detected: {det.pdf_kind} (sampled {det.sample_pages} pages)")
        self.progress.emit(5)

        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            pdf_for_text = cfg.pdf_path

            # OCR routing
            if cfg.ocr_mode != "never":
                self.log.emit("Running OCR (only if needed)…")
                out_ocr = td / "ocr.pdf"
                pdf_for_text = ocr_pdf_if_needed(
                    cfg.pdf_path,
                    out_pdf=out_ocr,
                    detected_kind=det.pdf_kind,
                    opts=OcrOptions(mode=cfg.ocr_mode, lang=cfg.ocr_lang),
                )
            self.progress.emit(20)

            self.log.emit("Extracting text…")
            pages = extract_text_by_page(pdf_for_text)
            pages_clean = [clean_text(p) for p in pages]
            (job_dir / "pages.txt.json").write_text(json.dumps(pages_clean, ensure_ascii=False, indent=2), encoding="utf-8")
            self.progress.emit(30)

            src_lang = cfg.src_lang or _guess_src_lang_basic(pages_clean) or "eng_Latn"
            if cfg.src_lang:
                self.log.emit(f"Source language: {src_lang}")
            else:
                self.log.emit(f"Source language auto: {src_lang} (set manually for best accuracy)")

            self.log.emit("Loading NLLB translator (first time can take a bit)…")
            translator = NllbTranslator(NllbConfig(model_name=cfg.nllb_model, use_mps_if_available=cfg.use_mps))
            self.progress.emit(35)

            self.log.emit("Translating pages…")
            translated_pages: List[str] = []
            total_pages = max(1, len(pages_clean))
            for i, p in enumerate(pages_clean, start=1):
                if not p.strip():
                    translated_pages.append("")
                else:
                    chunks = chunk_text(p, max_chars=cfg.max_chars)
                    tr_chunks = translator.translate_chunks(chunks, src_lang=src_lang, tgt_lang=cfg.target_lang)
                    translated_pages.append(" ".join(tr_chunks).strip())

                # 35..70
                pct = 35 + int((i / total_pages) * 35)
                self.progress.emit(min(70, max(35, pct)))

            (job_dir / "translated.txt.json").write_text(json.dumps(translated_pages, ensure_ascii=False, indent=2), encoding="utf-8")
            self.log.emit("Translation complete.")
            self.progress.emit(72)

            # TTS
            self.log.emit("Text-to-speech (Piper) → WAV chunks…")
            tts_opts = TtsOptions(
                voice_model=cfg.voice_model,
                fmt=cfg.audio_fmt,
                bitrate=cfg.audio_bitrate,
            )

            wavs: List[Path] = []
            nonempty = [p for p in translated_pages if p.strip()]
            denom = max(1, len(nonempty))
            done_pages = 0

            for page_i, p in enumerate(translated_pages, start=1):
                p = p.strip()
                if not p:
                    continue
                for ci, ch in enumerate(chunk_text(p, max_chars=cfg.max_chars), start=1):
                    out_wav = td / f"p{page_i:05d}_{ci:03d}.wav"
                    synthesize_wav(ch, tts_opts, out_wav)
                    wavs.append(out_wav)

                done_pages += 1
                # 72..92
                pct = 72 + int((done_pages / denom) * 20)
                self.progress.emit(min(92, max(72, pct)))

            if not wavs:
                raise RuntimeError("No audio chunks produced (no text extracted/translated?).")

            self.log.emit("Merging + encoding audio…")
            full_wav = td / "book.wav"
            concat_wavs(wavs, full_wav)

            out_audio = job_dir / f"{cfg.pdf_path.stem}.{cfg.audio_fmt}"
            encode_audio(full_wav, out_audio, cfg.audio_fmt, cfg.audio_bitrate)

        meta: Dict[str, object] = {
            "job_id": job_id,
            "pdf": str(cfg.pdf_path),
            "pdf_kind": det.pdf_kind,
            "src_lang": src_lang,
            "target_lang": cfg.target_lang,
            "audio_path": str(out_audio),
            "job_dir": str(job_dir),
        }
        (job_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        self.progress.emit(100)
        self.log.emit("Done ✅")
        self.done.emit(meta)


class RagWorker(QObject):
    log = Signal(str)
    done = Signal(dict)
    error = Signal(str)

    def __init__(self, outputs_dir: Path, job_id: str, chroma_dir: Path, *, ollama_url: str, embed_model: str) -> None:
        super().__init__()
        self.outputs_dir = outputs_dir
        self.job_id = job_id
        self.chroma_dir = chroma_dir
        self.ollama_url = ollama_url
        self.embed_model = embed_model

    def run(self) -> None:
        try:
            job_dir = self.outputs_dir / self.job_id
            translated = job_dir / "translated.txt.json"
            if not translated.exists():
                raise RuntimeError("Missing translated.txt.json (convert first).")

            pages = json.loads(translated.read_text(encoding="utf-8"))
            self.log.emit("Indexing into Chroma…")
            rag = RagIndex(RagConfig(persist_dir=self.chroma_dir, embed_model=self.embed_model, ollama_base_url=self.ollama_url))
            doc_id = stable_doc_id(self.job_id)
            stats = rag.ingest_pages(doc_id, pages, field="translated")
            out = {"job_id": self.job_id, "doc_id": doc_id, **stats}
            self.done.emit(out)
        except Exception as e:
            self.error.emit(str(e))


class AskWorker(QObject):
    done = Signal(dict)
    error = Signal(str)

    def __init__(self, chroma_dir: Path, job_id: str, question: str, *, ollama_url: str, embed_model: str, llm_model: str, top_k: int) -> None:
        super().__init__()
        self.chroma_dir = chroma_dir
        self.job_id = job_id
        self.question = question
        self.ollama_url = ollama_url
        self.embed_model = embed_model
        self.llm_model = llm_model
        self.top_k = top_k

    def run(self) -> None:
        try:
            rag = RagIndex(RagConfig(
                persist_dir=self.chroma_dir,
                embed_model=self.embed_model,
                llm_model=self.llm_model,
                ollama_base_url=self.ollama_url,
            ))
            doc_id = stable_doc_id(self.job_id)
            out = rag.answer(doc_id, self.question, k=self.top_k)
            self.done.emit(out)
        except Exception as e:
            self.error.emit(str(e))

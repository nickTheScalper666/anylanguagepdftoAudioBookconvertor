from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QLineEdit, QComboBox, QTextEdit, QProgressBar, QMessageBox,
    QSplitter, QGroupBox, QFormLayout, QSpinBox
)

from .widgets import DropZone
from .worker import UiConvertConfig, ConvertWorker, RagWorker, AskWorker

APP_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = Path.home() / "Documents" / "book2audio_outputs"
DEFAULT_CHROMA = APP_ROOT / "data" / "chroma"
DEFAULT_VOICES = APP_ROOT / "voices"

COMMON_LANGS = [
    ("English", "eng_Latn"),
    ("Spanish", "spa_Latn"),
    ("French", "fra_Latn"),
    ("German", "deu_Latn"),
    ("Italian", "ita_Latn"),
    ("Portuguese", "por_Latn"),
    ("Hindi", "hin_Deva"),
    ("Arabic", "arb_Arab"),
    ("Japanese", "jpn_Jpan"),
    ("Korean", "kor_Hang"),
    ("Chinese (Simplified)", "zho_Hans"),
    ("Chinese (Traditional)", "zho_Hant"),
]

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("book2audio — PDF → Translate → Audiobook (local)")

        self.pdf_path: Path | None = None
        self.voice_path: Path = self._pick_default_voice()
        self.out_dir: Path = DEFAULT_OUT
        self.last_job_id: str | None = None

        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)

        splitter = QSplitter(Qt.Horizontal)
        outer.addWidget(splitter)

        left = QWidget()
        right = QWidget()
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        # Left: drop zone + controls + log
        l = QVBoxLayout(left)
        self.drop = DropZone()
        self.drop.file_dropped.connect(self._on_pdf_selected)
        l.addWidget(self.drop)

        btn_row = QHBoxLayout()
        self.btn_browse = QPushButton("Browse PDF…")
        self.btn_browse.clicked.connect(self._browse_pdf)
        btn_row.addWidget(self.btn_browse)

        self.btn_convert = QPushButton("Convert → Audiobook")
        self.btn_convert.clicked.connect(self._start_convert)
        self.btn_convert.setEnabled(False)
        btn_row.addWidget(self.btn_convert)

        l.addLayout(btn_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        l.addWidget(self.progress)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        l.addWidget(self.log, 1)

        # Right: settings + Ask AI
        r = QVBoxLayout(right)

        settings = QGroupBox("Settings")
        form = QFormLayout(settings)

        # Output dir
        out_row = QHBoxLayout()
        self.out_edit = QLineEdit(str(self.out_dir))
        self.out_edit.setReadOnly(True)
        self.btn_out = QPushButton("Change…")
        self.btn_out.clicked.connect(self._browse_out_dir)
        out_row.addWidget(self.out_edit, 1)
        out_row.addWidget(self.btn_out)
        form.addRow("Output folder", out_row)

        # Voice
        voice_row = QHBoxLayout()
        self.voice_edit = QLineEdit(str(self.voice_path) if self.voice_path else "")
        self.voice_edit.setReadOnly(True)
        self.btn_voice = QPushButton("Choose…")
        self.btn_voice.clicked.connect(self._browse_voice)
        voice_row.addWidget(self.voice_edit, 1)
        voice_row.addWidget(self.btn_voice)
        form.addRow("Piper voice (.onnx)", voice_row)

        # Languages
        self.src_edit = QLineEdit("")
        self.src_edit.setPlaceholderText("Optional (best accuracy): e.g., eng_Latn")
        form.addRow("Source lang (NLLB)", self.src_edit)

        tgt_row = QHBoxLayout()
        self.tgt_combo = QComboBox()
        for name, code in COMMON_LANGS:
            self.tgt_combo.addItem(f"{name} ({code})", code)
        self.tgt_manual = QLineEdit("")
        self.tgt_manual.setPlaceholderText("or type code (e.g., spa_Latn)")
        tgt_row.addWidget(self.tgt_combo, 1)
        tgt_row.addWidget(self.tgt_manual, 1)
        form.addRow("Target lang", tgt_row)

        # OCR
        self.ocr_mode = QComboBox()
        self.ocr_mode.addItems(["auto", "never", "force"])
        form.addRow("OCR mode", self.ocr_mode)

        self.ocr_lang = QLineEdit("eng")
        self.ocr_lang.setPlaceholderText("Tesseract: eng / spa / eng+spa …")
        form.addRow("OCR language", self.ocr_lang)

        # NLLB model
        self.nllb_model = QLineEdit("facebook/nllb-200-distilled-600M")
        form.addRow("NLLB model", self.nllb_model)

        # Chunk size
        self.max_chars = QSpinBox()
        self.max_chars.setRange(600, 4000)
        self.max_chars.setValue(1800)
        form.addRow("Chunk size (chars)", self.max_chars)

        # Audio format / bitrate
        fmt_row = QHBoxLayout()
        self.audio_fmt = QComboBox()
        self.audio_fmt.addItems(["m4b", "mp3", "wav"])
        self.bitrate = QLineEdit("128k")
        self.bitrate.setPlaceholderText("128k")
        fmt_row.addWidget(self.audio_fmt, 1)
        fmt_row.addWidget(QLabel("Bitrate"))
        fmt_row.addWidget(self.bitrate, 1)
        form.addRow("Audio", fmt_row)

        r.addWidget(settings)

        # Result actions
        actions = QGroupBox("After conversion")
        a = QVBoxLayout(actions)
        self.btn_open_output = QPushButton("Open output folder")
        self.btn_open_output.clicked.connect(self._open_output_folder)
        self.btn_open_output.setEnabled(False)
        a.addWidget(self.btn_open_output)

        self.btn_index = QPushButton("Index for Ask-AI")
        self.btn_index.clicked.connect(self._start_index)
        self.btn_index.setEnabled(False)
        a.addWidget(self.btn_index)

        r.addWidget(actions)

        # Ask AI box
        ask = QGroupBox("Ask-AI (local)")
        af = QFormLayout(ask)

        self.ollama_url = QLineEdit("http://127.0.0.1:11434")
        af.addRow("Ollama URL", self.ollama_url)

        self.embed_model = QLineEdit("nomic-embed-text")
        af.addRow("Embedding model", self.embed_model)

        self.llm_model = QLineEdit("qwen2.5:7b-instruct")
        af.addRow("LLM model", self.llm_model)

        self.top_k = QSpinBox()
        self.top_k.setRange(1, 12)
        self.top_k.setValue(5)
        af.addRow("Top-K", self.top_k)

        q_row = QHBoxLayout()
        self.question = QLineEdit("")
        self.question.setPlaceholderText("Ask about the document…")
        self.btn_ask = QPushButton("Ask")
        self.btn_ask.clicked.connect(self._start_ask)
        self.btn_ask.setEnabled(False)
        q_row.addWidget(self.question, 1)
        q_row.addWidget(self.btn_ask)
        af.addRow("Question", q_row)

        self.answer = QTextEdit()
        self.answer.setReadOnly(True)
        self.answer.setMinimumHeight(160)
        af.addRow("Answer", self.answer)

        r.addWidget(ask, 1)

        self._append_log("Ready. Drop a PDF to begin.")

    def _pick_default_voice(self) -> Path:
        # Pick first .onnx in voices dir if available
        if DEFAULT_VOICES.exists():
            for p in sorted(DEFAULT_VOICES.glob("*.onnx")):
                return p
        return DEFAULT_VOICES / "en_US-lessac-medium.onnx"

    def _append_log(self, msg: str) -> None:
        self.log.append(msg)

    def _on_pdf_selected(self, path: str) -> None:
        self.pdf_path = Path(path)
        self.drop.set_path(path)
        self.btn_convert.setEnabled(True)
        self.progress.setValue(0)
        self._append_log(f"Selected: {path}")

    def _browse_pdf(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, "Choose PDF", str(Path.home()), "PDF files (*.pdf)")
        if p:
            self._on_pdf_selected(p)

    def _browse_voice(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, "Choose Piper voice (.onnx)", str(DEFAULT_VOICES), "ONNX (*.onnx)")
        if p:
            self.voice_path = Path(p)
            self.voice_edit.setText(str(self.voice_path))

    def _browse_out_dir(self) -> None:
        p = QFileDialog.getExistingDirectory(self, "Choose output folder", str(self.out_dir))
        if p:
            self.out_dir = Path(p)
            self.out_edit.setText(str(self.out_dir))

    def _open_output_folder(self) -> None:
        if not self.last_job_id:
            return
        job_dir = self.out_dir / self.last_job_id
        if job_dir.exists():
            QDesktopServices.openUrl(job_dir.as_uri())
        else:
            QDesktopServices.openUrl(self.out_dir.as_uri())

    def _target_lang(self) -> str:
        manual = self.tgt_manual.text().strip()
        if manual:
            return manual
        return str(self.tgt_combo.currentData())

    def _start_convert(self) -> None:
        if not self.pdf_path:
            QMessageBox.warning(self, "Missing PDF", "Drop or choose a PDF first.")
            return

        self.progress.setValue(0)
        self.btn_convert.setEnabled(False)
        self.btn_open_output.setEnabled(False)
        self.btn_index.setEnabled(False)
        self.btn_ask.setEnabled(False)
        self.answer.clear()

        cfg = UiConvertConfig(
            pdf_path=self.pdf_path,
            out_dir=self.out_dir,
            voice_model=Path(self.voice_edit.text()).expanduser(),
            src_lang=self.src_edit.text().strip() or None,
            target_lang=self._target_lang(),
            ocr_mode=self.ocr_mode.currentText(),
            ocr_lang=self.ocr_lang.text().strip() or "eng",
            max_chars=int(self.max_chars.value()),
            nllb_model=self.nllb_model.text().strip() or "facebook/nllb-200-distilled-600M",
            use_mps=True,
            audio_fmt=self.audio_fmt.currentText(),
            audio_bitrate=self.bitrate.text().strip() or "128k",
        )

        self._append_log("Starting conversion…")

        self.thread = QThread(self)
        self.worker = ConvertWorker(cfg)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.log.connect(self._append_log)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.done.connect(self._on_convert_done)
        self.worker.error.connect(self._on_convert_error)

        self.worker.done.connect(self.thread.quit)
        self.worker.done.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.worker.error.connect(self.thread.quit)
        self.worker.error.connect(self.worker.deleteLater)

        self.thread.start()

    def _on_convert_done(self, meta: dict) -> None:
        self.last_job_id = str(meta.get("job_id"))
        audio_path = str(meta.get("audio_path", ""))
        self._append_log(f"Output audio: {audio_path}")
        self.btn_convert.setEnabled(True)
        self.btn_open_output.setEnabled(True)
        self.btn_index.setEnabled(True)

    def _on_convert_error(self, err: str) -> None:
        self._append_log(f"ERROR: {err}")
        QMessageBox.critical(self, "Convert failed", err)
        self.btn_convert.setEnabled(True)

    def _start_index(self) -> None:
        if not self.last_job_id:
            QMessageBox.warning(self, "No job", "Convert a PDF first.")
            return

        self.btn_index.setEnabled(False)
        self.btn_ask.setEnabled(False)
        self._append_log("Indexing for Ask-AI…")

        DEFAULT_CHROMA.mkdir(parents=True, exist_ok=True)

        self.index_thread = QThread(self)
        self.index_worker = RagWorker(
            outputs_dir=self.out_dir,
            job_id=self.last_job_id,
            chroma_dir=DEFAULT_CHROMA,
            ollama_url=self.ollama_url.text().strip() or "http://127.0.0.1:11434",
            embed_model=self.embed_model.text().strip() or "nomic-embed-text",
        )
        self.index_worker.moveToThread(self.index_thread)

        self.index_thread.started.connect(self.index_worker.run)
        self.index_worker.log.connect(self._append_log)
        self.index_worker.done.connect(self._on_index_done)
        self.index_worker.error.connect(self._on_index_error)

        self.index_worker.done.connect(self.index_thread.quit)
        self.index_worker.done.connect(self.index_worker.deleteLater)
        self.index_thread.finished.connect(self.index_thread.deleteLater)

        self.index_worker.error.connect(self.index_thread.quit)
        self.index_worker.error.connect(self.index_worker.deleteLater)

        self.index_thread.start()

    def _on_index_done(self, out: dict) -> None:
        self._append_log(f"Indexed ✅ chunks={out.get('chunks_indexed')}")
        self.btn_index.setEnabled(True)
        self.btn_ask.setEnabled(True)

    def _on_index_error(self, err: str) -> None:
        self._append_log(f"Index ERROR: {err}")
        QMessageBox.critical(self, "Index failed", err)
        self.btn_index.setEnabled(True)

    def _start_ask(self) -> None:
        if not self.last_job_id:
            QMessageBox.warning(self, "No job", "Convert and index first.")
            return
        q = self.question.text().strip()
        if not q:
            return

        self.btn_ask.setEnabled(False)
        self.answer.setPlainText("Thinking… (local Ollama)")
        self.ask_thread = QThread(self)
        self.ask_worker = AskWorker(
            chroma_dir=DEFAULT_CHROMA,
            job_id=self.last_job_id,
            question=q,
            ollama_url=self.ollama_url.text().strip() or "http://127.0.0.1:11434",
            embed_model=self.embed_model.text().strip() or "nomic-embed-text",
            llm_model=self.llm_model.text().strip() or "qwen2.5:7b-instruct",
            top_k=int(self.top_k.value()),
        )
        self.ask_worker.moveToThread(self.ask_thread)

        self.ask_thread.started.connect(self.ask_worker.run)
        self.ask_worker.done.connect(self._on_ask_done)
        self.ask_worker.error.connect(self._on_ask_error)

        self.ask_worker.done.connect(self.ask_thread.quit)
        self.ask_worker.done.connect(self.ask_worker.deleteLater)
        self.ask_thread.finished.connect(self.ask_thread.deleteLater)

        self.ask_worker.error.connect(self.ask_thread.quit)
        self.ask_worker.error.connect(self.ask_worker.deleteLater)

        self.ask_thread.start()

    def _on_ask_done(self, out: dict) -> None:
        ans = str(out.get("answer", ""))
        cits = out.get("citations", [])
        if cits:
            pages = sorted({c.get("page") for c in cits if isinstance(c, dict) and c.get("page")})
            ans += "\n\nCitations: " + ", ".join([f"p.{p}" for p in pages])
        self.answer.setPlainText(ans)
        self.btn_ask.setEnabled(True)

    def _on_ask_error(self, err: str) -> None:
        self.answer.setPlainText(f"Ask-AI error: {err}\n\nMake sure Ollama is running and models are pulled.")
        self.btn_ask.setEnabled(True)

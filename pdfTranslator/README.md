# book2audio UI (PySide6) — drag & drop PDF → translated audiobook + Ask AI (local)

This is a **desktop UI** for macOS (Apple Silicon) that:
- lets you **drag & drop** a PDF (no path typing)
- detects TEXT / SCANNED / HYBRID
- OCRs only when needed (OCRmyPDF + Tesseract, via system install)
- extracts text (PyMuPDF)
- translates (NLLB)
- speaks (Piper)
- optional Ask-AI using **Ollama** + Chroma (with page citations)

---

## 1) Install system deps (macOS)
```bash
brew install ffmpeg tesseract ocrmypdf
```

## 2) Python env
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install piper-tts
```

## 3) Piper voice
Put a Piper voice in `voices/`:
- `voices/<voice>.onnx`
- `voices/<voice>.onnx.json`

## 4) Run the UI
```bash
python app.py
```

---

## Ask-AI (optional)
Install Ollama + pull models:
```bash
ollama pull qwen2.5:7b-instruct
ollama pull nomic-embed-text
```
Then in the UI:
- Convert → Index → Ask

---

## Notes
- For best translation accuracy, set the correct **NLLB source language code** (e.g., `eng_Latn`).
- OCR language should match the book language (Tesseract codes like `eng`, `spa`, `eng+spa`).

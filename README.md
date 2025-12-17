# anylanguagepdftoAudioBookconvertor
Convert any language pdf file with/without scanned images into an audiobook in any language. Supported formats include mp3, wav, m4b. Part of this install also includes a feature to call a local deep seek model for clarification regarding the outputted file. It will be indexed to your local Llm model. You can swap LLM and Parameters as desired


# Book2Audio (Desktop) — PDF → Translated Audiobook + Local Ask-AI

A local-first desktop app that converts PDFs into audiobooks, with optional OCR for scanned PDFs, optional translation (NLLB), and high-quality offline TTS (Piper). It also includes a local “Ask-AI” mode that indexes your PDF into a vector DB (Chroma) and answers questions using your local Ollama models.

## Features
- **PDF → Audio**: export as `m4b`, `mp3`, or `wav`
- **Scanned PDF support**: auto-detects text vs scanned and runs OCR (OCRmyPDF) when needed
- **Translation**: uses **NLLB** (Transformers) to translate into common target languages (or custom NLLB codes)
- **Offline TTS**: uses **Piper** voice models (`.onnx` + `.onnx.json`)
- **Ask-AI (local)**:
  - Builds an index with **ChromaDB**
  - Uses **Ollama** for embeddings + local LLM answers with page citations

---

## Project structure

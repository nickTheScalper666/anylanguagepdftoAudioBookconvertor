# anylanguagepdftoAudioConvertor


> Convert any language PDF into an audiobook with optional translation, OCR support, and local AI-powered Q&A

A local-first desktop application that transforms PDFs into high-quality audiobooks with optional translation and includes a powerful "Ask-AI" feature for querying your documents using local LLM models.

## ✨ Features

- **PDF to Audio Conversion**: Export as M4B, MP3, or WAV
- **Scanned PDF Support**: Auto-detects and applies OCR (OCRmyPDF) for image-based PDFs
- **Translation**: Translate content using NLLB-200 (200+ languages)
- **Offline TTS**: High-quality text-to-speech using Piper voice models
- **Ask-AI**: Query your PDFs using local Ollama models with page citations
  - Vector search with ChromaDB
  - Configurable embedding and LLM models
  - Full privacy - everything runs locally

## 📋 Prerequisites

### Required System Tools

#### 1. Ollama (for Ask-AI feature)
Install from [ollama.ai](https://ollama.ai)

```bash
# Verify installation
ollama --version
```

#### 2. FFmpeg (for audio encoding)
Download from [ffmpeg.org](https://ffmpeg.org)

```bash
# Verify installation
ffmpeg -version
```

#### 3. OCRmyPDF (for scanned PDFs)
Install from [ocrmypdf.readthedocs.io](https://ocrmypdf.readthedocs.io)

```bash
# Verify installation
ocrmypdf --version
```

> **Note**: OCRmyPDF includes Tesseract. On macOS, it installs automatically via Homebrew. You can still convert text PDFs without OCR installed.

#### 4. Piper (TTS engine)
Install from [github.com/rhasspy/piper](https://github.com/rhasspy/piper). Download for one for each language you want.

```bash
# Verify installation (try both)
piper --help
# or
python -m piper --help
```

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd book2audio
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate it
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows PowerShell
```

### 3. Install Python Dependencies

```bash
# Upgrade pip
pip install -U pip

# Install required packages
pip install \
  PySide6 \
  httpx \
  pymupdf \
  chromadb \
  langdetect \
  torch \
  transformers \
  sentencepiece
```

### 4. Download Models

#### Ollama Models (for Ask-AI)

```bash
# Start Ollama service
ollama serve

# Pull default models
ollama pull nomic-embed-text      # Embeddings
ollama pull qwen2.5:7b-instruct   # LLM

# Optional: DeepSeek R1 (larger, more capable)
ollama pull deepseek-r1:32b
```

#### NLLB Translation Model

The translation model (`facebook/nllb-200-distilled-600M`) downloads automatically on first use.

To pre-download:

```bash
python -c "from transformers import AutoTokenizer, AutoModelForSeq2SeqLM; \
m='facebook/nllb-200-distilled-600M'; \
AutoTokenizer.from_pretrained(m); \
AutoModelForSeq2SeqLM.from_pretrained(m); \
print('Downloaded:', m)"
```

#### Piper Voice Models

Example voices are included in the `voices/` directory.

To add more voices:
1. Download voice pairs from [Piper Voices](https://github.com/rhasspy/piper/releases)
2. Each voice needs two files:
   - `voice_name.onnx`
   - `voice_name.onnx.json`
3. Place both files in the `voices/` directory

## 📁 Project Structure

```
.
├── app.py              # Main application entry point
├── ui/                 # User interface components
├── book2audio/         # Core conversion logic
├── voices/             # Piper voice models (.onnx + .onnx.json)
└── data/
    └── chroma/         # Vector database (created on first index)
```

## 🎯 Usage

### Starting the Application

```bash
# Ensure virtual environment is activated
source .venv/bin/activate  # macOS/Linux

# Run the app
python app.py
```

### Converting a PDF to Audiobook

1. **Load PDF**: Drag & drop a PDF or click "Browse" to select
2. **Select Voice**: Choose a Piper `.onnx` voice from the `voices/` folder
3. **Choose Language**: Select target language or enter custom NLLB code
   - Examples: `spa_Latn` (Spanish), `jpn_Jpan` (Japanese), `fra_Latn` (French)
4. **OCR Settings**: 
   - `auto` - Recommended; detects if OCR is needed
   - `never` - Fastest; for text-based PDFs
   - `force` - Always apply OCR
5. **Convert**: Click the convert button and wait for processing
6. **Output**: Find your audiobook in the output folder

### Using Ask-AI

After converting a PDF:

1. Click **"Index for Ask-AI"** to build the vector database
2. Open the **Ask-AI** panel
3. Configure models (optional):
   - Embedding Model: `nomic-embed-text` (default)
   - LLM Model: `qwen2.5:7b-instruct` or `deepseek-r1:32b`
4. Ask questions about your PDF
5. Get answers with page citations (e.g., `[p.12]`)

## 🔧 Troubleshooting

### "ffmpeg not found"
- Install FFmpeg and ensure it's in your system PATH
- Restart your terminal after installation

### "ocrmypdf not found" / OCR fails
- Install OCRmyPDF and Tesseract
- Workaround: Set OCR mode to `never` for text-based PDFs

### Ask-AI connection errors
- Verify Ollama is running: `ollama serve`
- Check installed models: `ollama list`
- Confirm the URL in the app: `http://127.0.0.1:11434`

### Translation issues
- Ensure you have sufficient RAM (NLLB requires ~2GB)
- Check internet connection for first-time model download
- Use valid NLLB language codes

### Corrupted or incorrect index
- Delete the `data/chroma/` directory
- Re-index your PDF

## 🌍 Supported Languages

The NLLB-200 model supports over 200 languages. Common codes:

- English: `eng_Latn`
- Spanish: `spa_Latn`
- French: `fra_Latn`
- German: `deu_Latn`
- Chinese (Simplified): `zho_Hans`
- Japanese: `jpn_Jpan`
- Arabic: `arb_Arab`
- Russian: `rus_Cyrl`

[Full language code list](https://github.com/facebookresearch/flores/blob/main/flores200/README.md#languages-in-flores-200)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 🙏 Acknowledgments

- [Piper](https://github.com/rhasspy/piper) - High-quality TTS
- [NLLB](https://github.com/facebookresearch/fairseq/tree/nllb) - Translation models
- [Ollama](https://ollama.ai) - Local LLM inference
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF) - PDF OCR


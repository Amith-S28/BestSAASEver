# Setup Guide — Models to Download

You need **1 model in LM Studio** + **Chandra OCR 2 auto-downloads via pip** + **1 embedding model auto-downloads via Python**.

---

## 🧠 Model 1: Qwen3.5-9B (Synthesis LLM) — IN LM STUDIO

You're running: **`lmstudio-community/Qwen3.5-9B-MLX-4bit`**

This is the Apple Silicon-optimized MLX build — perfect for your M5 MacBook Pro.

### Setup Steps:
1. Open **LM Studio**
2. Load **Qwen3.5-9B-MLX-4bit** (you already have it downloaded)
3. Click **"Start Server"** on port `1234`
4. That's it — the pipeline connects to `http://127.0.0.1:1234/v1`

### Verify it's running:
```bash
curl http://127.0.0.1:1234/v1/models
```
You should see `lmstudio-community/Qwen3.5-9B-MLX-4bit` in the response.

---

## 🔬 Model 2: Chandra OCR 2 (PDF → Markdown) — AUTO-INSTALLED

**This is the SOTA OCR model** from your architecture doc. It's real, it's available, and it handles:
- Medical PDFs with complex layouts and tables
- Handwriting recognition
- 90+ languages
- Math formulas and charts

### How to install:
```bash
# Option A: Base install (uses pip's model download)
pip install chandra-ocr

# Option B: With HuggingFace backend (recommended for full control)
pip install "chandra-ocr[hf]"

# Option C: With MLX backend for Apple Silicon (FASTEST on your M5)
pip install "chandra-ocr[all]"
pip install mlx-vlm
```

### For Apple Silicon (your M5), use the MLX quantized version:
There's an **8-bit MLX build** at [jwindle47/chandra-ocr-2-8bit-mlx](https://huggingface.co/jwindle47/chandra-ocr-2-8bit-mlx) (~4.8 GB).

The pipeline automatically tries:
1. `chandra-mlx` (Apple Silicon optimized) → fastest
2. `chandra-hf` (HuggingFace transformers) → most compatible
3. `chandra-cli` (subprocess call to `chandra` command) → simplest
4. `pymupdf` (text-only) → last resort fallback

### First run will download ~4-5 GB of model weights.

---

## 📝 Model 3: Embedding Model — AUTO-DOWNLOADED

The **embedding model runs via Python** (sentence-transformers), NOT in LM Studio.
It downloads automatically the first time you run `medrag ingest`.

| Model | Auto-downloaded? | Size |
|-------|-----------------|------|
| `jinaai/jina-embeddings-v5-small` | ✅ Yes, on first use | ~1.3 GB |
| `BAAI/bge-small-en-v1.5` | ✅ Yes (fallback) | ~130 MB |

Pre-download if on slow connection:
```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('jinaai/jina-embeddings-v5-small', trust_remote_code=True)"
```

---

## 🧠 Memory Layout on Your 24GB M5

| Component | RAM | When Active |
|-----------|-----|-------------|
| macOS + apps | ~4.5 GB | Always |
| Qwen3.5-9B MLX 4-bit | ~5.5 GB | LM Studio server |
| Chandra OCR 2 MLX 8-bit | ~4.8 GB | During ingestion only |
| Jina v5 embeddings | ~1.5 GB | During ingest only |
| LanceDB (disk-backed) | ~0 GB | Always |
| **Headroom** | **~7.7 GB** | — |

> **Key insight:** Chandra OCR and the embedding model are only loaded during **ingestion**. During **querying**, only Qwen uses GPU memory. The pipeline can sequentially: load Chandra → unload → load Qwen for max precision.

---

## 🚀 Quick Start Checklist

- [ ] Open LM Studio → load **Qwen3.5-9B-MLX-4bit** → Start Server on port 1234
- [ ] `cd SaaSProject && cp .env.example .env`
- [ ] `pip install -e ".[chandra-mlx]"` (Apple Silicon optimized)
- [ ] Drop medical PDFs into `data/raw/`
- [ ] `medrag ingest data/raw/`
- [ ] `medrag query "What are the patient's cholesterol levels?"`

---

## 🔧 LM Studio Settings (Recommended)

In LM Studio's server settings:
- **Context Length:** 8192 (or 32768 — MLX 4-bit on 24GB can handle it)
- **GPU Offload:** Max (MLX uses Metal GPU natively)
- **Temperature:** 0.3 (set in .env, not LM Studio)

Your `.env` file:
```bash
LMSTUDIO_MODEL=lmstudio-community/Qwen3.5-9B-MLX-4bit
LMSTUDIO_MAX_CONTEXT=8192
LMSTUDIO_TEMPERATURE=0.3
OCR_ENGINE=chandra
EMBEDDING_MODEL=jinaai/jina-embeddings-v5-small
```
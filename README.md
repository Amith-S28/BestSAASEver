# Medical RAG: Local High-Precision Clinical Intelligence System

A fully local, privacy-preserving Retrieval-Augmented Generation (RAG) and clinical synthesis engine engineered for longitudinal patient records, multi-page diagnostic panels, and hereditary disease analysis. Powered by LanceDB, Jina Embeddings, Chandra OCR, NVIDIA NIM Rerankers, and a Next.js / Streamlit fullstack chat interface.

---

## 🏛️ System Architecture

```text
[Raw Medical PDF / Synthea Patient Record]
                 │
                 ▼
┌──────────────────────────────────────────────────────────┐
│ 1. INGESTION & PARSING                                   │
│ - Chandra OCR 2 vision-language parsing                  │
│ - MedRAG dataset downloader & Synthea synthetic records  │
│ - Rich streaming terminal progress bars                  │
└──────────────────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────┐
│ 2. ZERO-CHUNKING ATOMIC EMBEDDING                        │
│ - Jina-Embeddings-v5-Omni (32k token context window)     │
│ - Atomic vectorization preserving cross-table continuity │
└──────────────────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────┐
│ 3. IN-PROCESS HYBRID STORAGE (LanceDB)                   │
│ - Zero-copy Apache Arrow disk storage (0MB idle RAM)     │
│ - Reciprocal Rank Fusion (IVF-PQ Vector + Tantivy FTS)   │
└──────────────────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────┐
│ 4. PRECISION RERANKING & DYNAMIC SYNTHESIS               │
│ - NVIDIA NIM Reranker (nv-rerankqa-mistral-4b-v3)        │
│ - Dynamic LLM Router (Local LM Studio vs Cloud Tiers)    │
│ - Multi-turn conversational chat UI with citation links  │
└──────────────────────────────────────────────────────────┘
```

---

## ✨ Key Features & Recent Developments

- **Streaming Corpus Ingestion**: Real-time batch parsing with rich terminal progress bars, throughput telemetry, and non-blocking streaming.
- **Synthea & MedRAG Pipelines**: Automated generation and ingestion of synthetic multi-generational patient health records and official MedRAG clinical literature.
- **Dynamic Multi-Tier LLM Router**: Seamlessly shifts between offline local inference (via LM Studio) and cloud models (Nemotron, Ling, Laguna) based on intent complexity and data privacy modes.
- **Precision Reranking**: Optional NVIDIA NIM reranker to elevate top passage relevance before context synthesis.
- **Interactive Chat Interface**: Multi-session conversational UI with auto-title generation, response streaming, input locks, and citation footnotes.
- **Zero-Chunking Architecture**: Retains complete 32k-token patient histories as single documents, completely eliminating fragmented tables and broken laboratory reference ranges.

---

## 🛠️ Tech Stack

- **Storage & Vector Search**: LanceDB (Embedded Apache Arrow Columnar Engine, Tantivy FTS)
- **Embeddings**: Jina-Embeddings-v5-Omni-Small (32k context)
- **OCR / Parsing**: Chandra OCR 2 (5B VLM)
- **Reranker**: NVIDIA NIM (`nv-rerankqa-mistral-4b-v3`)
- **LLM Routing**: Local (LM Studio / Qwen 2.5) & Cloud Inference (Nemotron 3 Ultra, Ling, Laguna)
- **UI & Interaction**: Python, Rich CLI, and Next.js / Streamlit web interface

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- LM Studio (optional, for local offline LLM synthesis)

### 2. Installation
```bash
git clone https://github.com/Amith-S28/BestSAASEver.git
cd BestSAASEver
pip install -e .
```

### 3. Environment Configuration
Copy `.env.example` to `.env` and set your endpoints:
```env
LANCEDB_URI=data/lancedb
EMBEDDING_MODEL=jina-embeddings-v5-omni-small
MODE=local # or cloud
NVIDIA_API_KEY=nvapi-... # Optional NIM reranker
```

### 4. Ingestion & Chat
```bash
# Ingest synthetic medical records or clinical PDFs
python -m src.ingest --source data/raw

# Launch conversational RAG chat
python -m src.chat
```

---

## 📄 Documentation

- [Local LM Studio Configuration Guide](LM_STUDIO_SETUP.md)
- Complete design system guidelines in `design-system/`

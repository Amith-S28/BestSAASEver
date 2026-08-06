# Technical Architecture Report: Local High-Precision Medical RAG System

---

## 1. Executive Summary

This report outlines the technical architecture for a fully local, privacy-preserving Retrieval-Augmented Generation (RAG) system specialized in parsing, indexing, and synthesizing complex medical documents (such as multi-page longitudinal clinical histories, dense lab panels, and diagnostic reports).

The core architectural directive is to maximize local hardware efficiency while maintaining absolute clinical data integrity. By leveraging state-of-the-art vision-language parsers, long-context embedding models, and an in-process columnar vector database, this system operates entirely offline. This setup eliminates third-party data leaks, avoids cloud API latency, and circumvents the high memory overhead typically associated with enterprise vector databases.

---

## 2. Target Hardware Baseline

The system is optimized for native deployment on Apple Silicon hardware with unified memory architectures.

* **Processor:** Apple MacBook Pro M5
* **Memory Configuration:** 24GB Unified Memory
* **System Characteristics:** The unified memory architecture allows the CPU and GPU to share a high-bandwidth memory pool, eliminating the latency of PCIe data transfers between system RAM and dedicated VRAM.
* **Memory Target:** The runtime memory map is hard-capped at **~16GB of active utilization**, reserving a comfortable 8GB buffer for the operating system and background tasks to prevent disk swapping.

---

## 3. Core Technical Stack

The architecture is divided into four cleanly decoupled layers, selected specifically for structural synergy and resource efficiency.

| Layer | Component | Technical Specifications | Strategic Role |
| --- | --- | --- | --- |
| **1. Ingestion / OCR** | **Chandra OCR 2** | 5B Vision-Language Model | Converts raw PDFs and image scans into structured, layout-preserved Markdown and native tables. |
| **2. Vectorization** | **Jina-Embeddings-v5-Omni-Small** | 1024-dimensional dense vectors, 32k token context window | Translates full, unbroken text blocks into dense multi-dimensional vectors. |
| **3. Storage & Search** | **LanceDB** | Serverless, Embedded, Apache Arrow Columnar Engine | Stores text and vector arrays directly on disk; runs native hybrid search. |
| **4. Synthesis Brain** | **Dynamic LLM Router** | Auto-routes: Local (LM Studio) or Cloud Tiers (Ling, Laguna, Nemotron) | Processes retrieved context to generate clinically coherent, citation-backed answers. |
| **5. Reranking (Opt.)**| **NVIDIA NIM Reranker** | nv-rerankqa-mistral-4b-v3 (API) | Reorders retrieved passages by clinical relevance before LLM synthesis. |

---

## 4. End-to-End Data Pipeline & Lifecycle

```text
[Raw PDF / Medical Scan]
          │
          ▼
┌────────────────────────────────────────────────────────┐
│ PHASE 1: INGESTION (Chandra OCR 2)                     │
│ - Vision-Language parsing of layout topology           │
│ - Preservation of decimal points and structured tables  │
└────────────────────────────────────────────────────────┘
          │
          ▼
   [Layout-Perfect Markdown String]
          │
          ▼
┌────────────────────────────────────────────────────────┐
│ PHASE 2: EMBEDDING (Jina-Embeddings-v5-Omni-Small)     │
│ - Document passed as a single atomic unit (No chunking)│
│ - 32k context preserves cross-page clinical relevancy  │
└────────────────────────────────────────────────────────┘
          │
          ▼
   [High-Density Vector + Raw Markdown Payload]
          │
          ▼
┌────────────────────────────────────────────────────────┐
│ PHASE 3: STORAGE & INDEXING (LanceDB)                  │
│ - Persistent on-disk Apache Arrow write                │
│ - IVF-PQ Indexing (Vector) + Tantivy FTS Index (Text)  │
└────────────────────────────────────────────────────────┘
          │
          ▲
   [Hybrid Retrieval Loop via Reciprocal Rank Fusion (RRF)]
          │
          ▼
┌────────────────────────────────────────────────────────┐
│ PHASE 3.5: RERANKING (NVIDIA NIM) - Optional           │
│ - Reorders top passages by clinical relevance          │
└────────────────────────────────────────────────────────┘
          │
          ▼
┌────────────────────────────────────────────────────────┐
│ PHASE 4: SYNTHESIS (Dynamic LLM Router)                │
│ - Auto-routes to Local (LM Studio) or Cloud Tiers      │
│ - Context assembly from reranked document lookups      │
└────────────────────────────────────────────────────────┘

```

### Phase 1: Structural Extraction

When a medical document (PDF, TIFF, or high-resolution photo) enters the system, Chandra OCR 2 reads the layout topology. Instead of outputting unformatted raw text, it generates a clean Markdown file. Complex clinical matrices—such as complete blood counts (CBC) or metabolic panels—are accurately transformed into Markdown data tables, ensuring numerical values remain bound to their respective row and column parameters.

### Phase 2: Atomic Vectorization

The extracted Markdown payload is passed directly to Jina-Embeddings-v5-Omni-Small. Because the embedder features a 32k context window, **traditional micro-chunking is completely eliminated**. An entire multi-page patient charts or extensive clinical history summary is treated as a single, unbroken block. This guarantees that mathematical relationships between different sections of the document are preserved natively within the vector space.

### Phase 3: Hybrid Disk-Backed Storage

The vector coordinates along with the raw Markdown text are committed directly to LanceDB. LanceDB operates in-process (similar to SQLite), writing data directly to disk in an Apache Arrow layout. It constructs two separate indices: an **IVF-PQ index** for semantic similarity searches, and a **Full-Text Search (FTS)** index powered by Tantivy for exact keyword matching.

### Phase 4: Intent-Driven Retrieval & Synthesis

When a query is made, LanceDB executes a hybrid search. It concurrently assesses semantic concepts and exact keyword strings. The top matches can optionally be refined by the **NVIDIA NIM Reranker** (`nv-rerankqa-mistral-4b-v3`) for higher clinical precision. The context is then passed to the **Dynamic LLM Router**, which classifies the query's intent and token volume. It automatically routes the request to either a local model (via LM Studio) or a free cloud tier (Ling 3.0 Flash, Laguna S 2.1, or Nemotron 3 Ultra). The selected model synthesizes the data and formulates a citation-backed response.

---

## 5. Key Engineering Trade-offs & Architecture Decisions

### Decision 1: Elimination of Document Chunking

* **The Traditional Approach:** RAG systems usually segment text every 512 to 1024 tokens, which fractures tables and breaks narrative continuity across multi-page medical charts.
* **The System Solution:** By utilizing a 32k token embedding window, documents are kept completely whole. This prevents data loss at arbitrary boundaries and reduces the backend complexity of tracking overlapping chunk boundaries.

### Decision 2: Inclusion of an Optional NIM Reranker and Cloud Router

* **The Rationale:** While hybrid search (RRF) is strong, adding an optional NVIDIA NIM Reranker significantly improves the clinical precision of the top passages sent to the LLM. Furthermore, the system is no longer strictly bound to a single local model. The new Dynamic LLM Router allows falling back to powerful cloud models (like Nemotron 550B) for complex reasoning (e.g., hereditary disease patterns), while still supporting a fully offline `MODE=local` execution for privacy-strict environments.

### Decision 3: Serverless Embedded Storage over Heavy Daemons

* **The Rationale:** Databases like Weaviate, Milvus, and pgvector require running independent server daemons, Docker containers, or external background binaries (such as Weaviate's background Go runtime). On a 24GB laptop, these background engines aggressively consume memory caches. LanceDB operates with a **0MB idle RAM footprint**, leaving the maximum available memory completely open for model inference.

---

## 6. Runtime Resource Optimization & Memory Map

Unified memory allocation on the M5 chip is balanced to optimize precision without causing out-of-memory errors or system instability.

### Concurrent Memory Allocation Profile

* **System Overhead (macOS / UI / Active Apps):** ~4.5 GB
* **Chandra OCR 2 (5B Parameters, 4-bit Quantization):** ~3.5 GB
* **Embedding (Jina v5 Omni-Small):** ~1.5 GB
* **LanceDB (Zero-copy memory mapped files via Arrow):** ~0.0 GB
* **Local Synthesis (if MODE=local, e.g., via LM Studio):** ~6.5 GB
* **Available System Headroom (Safety Buffer):** **~8.0 GB**

### Sequential Memory Management Strategy (Optional Acceleration)

To unlock maximum precision, the pipeline can implement a sequential execution lifecycle:

1. **Ingestion State:** Initialize Chandra OCR 2 and local embedding models. Parse raw files into LanceDB.
2. **Purge State:** Clear Chandra OCR 2 from system memory, reclaiming ~3.5GB of VRAM.
3. **Inference State:** Load local LLM variants into LM Studio (if running `MODE=local`) or rely on cloud routing, keeping system overhead minimal during active chat sessions.

---

## 7. Next Steps: Phased Implementation Framework

* **Phase 1: Environment & Storage Setup** — Initialize the physical directory structure for LanceDB, declare the schema constraints, and verify the Apache Arrow table configurations.
* **Phase 2: Ingestion & Model Pipeline Integration** — Interface with Chandra OCR 2's local execution instance to handle text serialization and feed output into the Jina v5 embedder.
* **Phase 3: Synthesis Orchestration** — Establish the local inference container for Qwen 3.5 9B, implement strict medical formatting system instructions, and enforce exact document citation protocols.

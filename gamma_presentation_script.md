# Local Health-Data RAG System

## 1. Local Health-Data RAG: Architecture & Implementation
* **Vision:** A privacy-first, secure retrieval and synthesis engine running entirely on local consumer hardware.
* **Core Benefit:** Complete patient data privacy by eliminating cloud dependencies.
* **Objective:** Deliver state-of-the-art clinical context reasoning and zero-leakage search capability.

---

## 2. Hardware Environment & Sequential Execution
* **Host Machine:** MacBook Pro M5 with 24GB Unified Memory.
* **Compute Footprint:** Strictly optimized to stay within ~16GB active RAM, leaving an 8GB system buffer.
* **Sequential Model:** Ingestion (parsing/embedding) and inference spaces run sequentially to prevent memory contention.

---

## 3. Layer 1: Document Ingestion with Chandra OCR 2
* **Ingestion Model:** Chandra OCR 2 (5B Vision-Language Model).
* **High-Fidelity Extraction:** Translates scanned patient records and lab reports into layout-preserved Markdown.
* **Data Integrity:** Retains structural tables and precise alignment between medical labels and numerical values.

---

## 4. Layer 2: Embedding Engine & High Context Window
* **Embedding Model:** Jina-Embeddings-v5-Omni-Small (configured for Text execution).
* **Compute footprint:** ~700M active parameters.
* **Context Capacity:** Native 32,768 token context window to embed deep clinical profiles and multi-page documents in one pass.

---

## 5. Architecture: The "No Chunking" Paradigm
* **Traditional Approach vs. Our Solution:** Standard RAG uses arbitrary chunk splitting which breaks tables and disjoints context. We eliminate chunking.
* **Atomic Blocks:** Documents are ingested as single, unbroken layout blocks.
* **Clinical Integrity:** Preserves the complete context of long laboratory panels and continuous medical histories.

---

## 6. Layer 3: Serverless Storage via LanceDB
* **Database Choice:** LanceDB (embedded, serverless).
* **Format:** Columnar storage backed by Apache Arrow.
* **Infrastructure:** Zero external server management, allowing direct disk-backed reading/writing and seamless scaling.

---

## 7. Retrieval Strategy: Dual-Index Hybrid Search
* **Semantic Retrieval:** IVF-PQ vector index for deep semantic context and conceptual matching.
* **Keyword Retrieval:** Tantivy-based Full-Text Search (FTS) for exact drug names, units, and alphanumeric clinical codes.
* **Ranking Engine:** Reciprocal Rank Fusion (RRF) to blend and rank the hybrid search results.

---

## 8. Latency Optimization: Eliminating the Reranker
* **No Reranker in Phase 1:** A local Cross-Encoder reranker is omitted to avoid computational redundancy.
* **Low Candidate Counts:** The "No Chunking" approach naturally reduces the count of candidate retrieved blocks.
* **Efficiency Gains:** Slashing latency and freeing up memory resources while keeping search highly precise via native RRF.

---

## 9. Layer 4: Synthesis Brain via Qwen 3.5 9B Instruct
* **Synthesis Model:** Qwen 3.5 9B Instruct.
* **Quantization:** Runs locally using Q5_K_M or Q8_0 quantizations.
* **Capabilities:** Advanced medical domain understanding and clinical logic, synthesizing retrieved layout-preserved Markdown directly.

---

## 10. Execution Roadmap & Next Steps
* **Phase 1 Ingestion:** Initialize LanceDB local scheme and define tables.
* **Phase 2 Schema:** Configure Jina v5 embedding definitions inside the LanceDB schema.
* **Phase 3 Pipeline:** Establish OCR-to-vector processing pipeline for layout-preserved documents.

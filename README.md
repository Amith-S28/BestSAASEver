# MedRAG v2.0: Institutional-Grade Clinical AI Intelligence SaaS Platform

[![Architecture: Hexagonal](https://img.shields.io/badge/Architecture-Hexagonal%20Ports%20%26%20Adapters-blue)](file:///d:/Projects/RAG/BestSAASEver/tech/hexagonal-architecture.md)
[![Safety: Deterministic NLI](https://img.shields.io/badge/Safety-Deterministic%20NLI%20Verification-green)](file:///d:/Projects/RAG/BestSAASEver/tech/nli-verification-engine.md)
[![Compliance: HIPAA / Safe Harbor](https://img.shields.io/badge/Compliance-HIPAA%20Safe%20Harbor-purple)](file:///d:/Projects/RAG/BestSAASEver/prd/security-hipaa-dpdp.md)
[![Tests: 54 Passing](https://img.shields.io/badge/Tests-54%20Passing%20(100%25)-success)](file:///d:/Projects/RAG/BestSAASEver/tests)

MedRAG v2.0 is an institutional-grade, multi-tenant Clinical AI Intelligence platform designed for hospital networks, clinical research organizations, and diagnostic consult teams. It delivers sub-second longitudinal patient history synthesis cross-referenced against verified clinical textbooks and guidelines, backed by deterministic Natural Language Inference (NLI) sentence-level claim verification.

---

## 🏛️ Architectural Invariants

1. **Hexagonal Domain Isolation**: Pure clinical domain entities in `src/medrag/domain/` import zero external libraries, frameworks, or drivers. All capabilities are accessed via typed protocols in `src/medrag/ports/` (machine-enforced by AST import linter).
2. **Deterministic Claim-to-Evidence Audit**: Every clinical synthesis output undergoes sentence-level tokenization and NLI entailment scoring against retrieved evidence chunks (`P(Contradiction) >= 0.60` triggers automatic redaction with standard safety tombstones).
3. **Zero-Loss Longitudinal Ingestion**: HL7 FHIR R4 JSON bundles are parsed into immutable clinical timelines preserving encounters, observations, medication requests, and reference intervals. Multi-column lab PDFs use layout-aware parsing with LOINC linking.
4. **Zero-Copy In-Process Hybrid Storage**: LanceDB (Apache Arrow columnar memory) coupled with Tantivy lexical BM25 and Reciprocal Rank Fusion (RRF) delivers sub-10ms retrieval with zero idle RAM overhead.
5. **Strict Multi-Tenant PHI Isolation**: Compound tenant predicates (`tenant_id`, `clinic_id`, `patient_id`) enforced across all queries with HIPAA Safe Harbor de-identification.

---

## 📂 Repository Structure

```text
BestSAASEver/
├── prd/                         # 15 Product Requirement Documents (OnRent standard)
├── tech/                        # 23 Technical Architecture Specs & OpenAPI 3.1 contract
├── .cursor/rules/               # 15 Machine-enforced coding & architecture rules
├── scripts/                     # Pre-commit, CI, AST linter, MedQA benchmarks & Air-gap packager
├── src/medrag/
│   ├── domain/                  # Pure clinical domain models & typed exceptions (zero deps)
│   ├── ports/                   # Abstract protocol interfaces (8 Port Protocols)
│   ├── application/             # Use cases, prompt composer, claim auditor, CMO override
│   ├── infrastructure/          # Adapters (LanceDB Arrow, NLI verifier, Embedder, Reranker)
│   └── interfaces/              # FastAPI REST/SSE endpoints, Clinician Workspace UI, CLI
├── tests/                       # Unit (domain, infra, services), integration (api), benchmarks
├── Dockerfile                   # Multi-stage hardened production container
├── docker-compose.yml           # Multi-service production orchestration
└── airgap_manifest.json         # SHA-256 verified air-gapped hospital deployment manifest
```

---

## 🚀 Quickstart & Clinician Workspace

### 1. Requirements
- Python >= 3.11 (tested on Python 3.12)
- Virtual environment

### 2. Run the MedRAG Server & UI
```bash
# Launch the API server and Clinician Workspace
.venv\Scripts\python src/medrag/interfaces/cli.py serve --port 8000
```
Open **`http://localhost:8000/`** in your browser to interact with the **MedRAG Clinician Workspace**:
- **Patient Explorer**: Longitudinal timeline, encounter cards, abnormal lab trajectory alerts (`[K+] 6.2 mEq/L`, `Creatinine 3.4 mg/dL`).
- **Streaming Synthesis**: Real-time SSE token stream, inline citations (`[^1]`), and contradiction safety tombstones.
- **Evidence Drawer**: Verbatim clinical excerpts from KDIGO, Harrison's, and ACC/AHA guidelines with NLI scores.
- **CMO Override Modal**: Human-in-the-loop Four-Eyes review modal for chief medical officers.

---

## 💻 Unified CLI Commands

The unified CLI (`src/medrag/interfaces/cli.py`) supports core institutional operations:

```bash
# Check subsystem health & telemetry (LanceDB, NLI verifier, worker, LLM)
.venv\Scripts\python src/medrag/interfaces/cli.py health

# Run AST Domain Isolation linter (ensures 0 external imports in domain/)
.venv\Scripts\python src/medrag/interfaces/cli.py lint

# Run MedQA clinical scenario evaluation harness
.venv\Scripts\python src/medrag/interfaces/cli.py benchmark

# Generate air-gapped hospital deployment checksum manifest
.venv\Scripts\python src/medrag/interfaces/cli.py airgap
```

---

## 🧪 Automated Testing

MedRAG features a comprehensive test suite covering pure domain logic, storage adapters, FHIR/PDF ingestion, NLI contradiction redaction, REST/SSE streaming endpoints, and MedQA clinical benchmarks.

```bash
# Run all 54 tests
.venv\Scripts\python -m pytest tests/ -v
```

---

## 🐳 Production Deployment

### Docker Multi-Stage Container
```bash
docker build -t medrag:2.0.0 .
docker run -p 8000:8000 medrag:2.0.0
```

### Docker Compose (API + Redis + LanceDB Persistent Volumes)
```bash
docker compose up -d
```

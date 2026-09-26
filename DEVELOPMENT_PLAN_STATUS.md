# MedRAG v2.0: Living Development Plan & Sprint Status

_Tracking Active Tasks, Completed Milestones, and Quality Gates_  
_Updated: 2026-09-25 | Standardized against Institutional SaaS Engineering Governance_

---

## Sprint Overview

| Sprint | Focus Area | Status | Deliverables Completed |
|---|---|---|---|
| **Sprint 1** | Governance, Specs & Machine Enforcement | 🟢 Completed | PRDs (15), Tech Specs (23), Cursor Rules (15), AST Linter |
| **Sprint 2** | Pure Hexagonal Domain & Port Protocols | 🟢 Completed | Domain entities, typed exceptions, 8 Port Protocols, 100% tests |
| **Sprint 3** | Model Loading De-Risk & In-Process Storage | 🟢 Completed | LanceDB adapter, RRF fusion, SNOMED/RxNorm linker, embedder/reranker |
| **Sprint 4** | Dual-Track Ingestion & Async Worker | 🟢 Completed | FHIR R4 parser, PDF parser, Redis/Memory worker, distributed locks |
| **Sprint 5** | Synthesis Engine & Deterministic NLI Audit | 🟢 Completed | Prompt composer, DeBERTa verifier, CMO override, contradiction filter |
| **Sprint 6** | SaaS API, Multi-Tenancy & Streaming | 🟢 Completed | FastAPI endpoints, JWT auth, RBAC, rate limiter, SSE streaming, audit log |
| **Sprint 7** | Benchmark Harness & Model Validation | 🟢 Completed | MedQA evaluation harness, threshold calibration, licensing audit |
| **Sprint 8** | Clinician Workspace UI | 🟢 Completed | Responsive glassmorphic UI, timeline explorer, streaming synthesis, CMO modal |
| **Sprint 9** | Admin Console, Polish & Deployment | 🟢 Completed | Multi-stage Dockerfile, docker-compose, air-gap packager, unified CLI |

---

## Detailed Task Breakdown & Verification Matrix

### Sprint 1: Governance & Machine Enforcement
- [x] **Task 1.1**: Clean repository workspace retaining UI/UX Pro Max skill.
- [x] **Task 1.2**: Scaffolding baseline config (`pyproject.toml`, `.gitignore`, `.env.example`, `README.md`).
- [x] **Task 1.3**: Author all 15 Product Requirement Documents (`prd/*.md`).
- [x] **Task 1.4**: Author all 23 Technical Architecture Specifications (`tech/*.md` + `openapi-spec.yml`).
- [x] **Task 1.5**: Author all 15 Machine-Enforced Coding Rules (`.cursor/rules/*.md`).
- [x] **Task 1.6**: Implement AST-level Domain Boundary Linter (`scripts/lint_domain_imports.py`).
- [x] **Task 1.7**: Setup pre-commit configuration (`.pre-commit-config.yaml`).
- [x] **Exit Gate 1**: All specifications reviewed, pre-commit gate active, AST linter tested.

### Sprint 2: Pure Domain Layer & Ports
- [x] **Task 2.1**: Implement `src/medrag/domain/exceptions.py` (ClinicalException hierarchy).
- [x] **Task 2.2**: Implement `src/medrag/domain/patient.py` (PatientTimeline, encounters, observations).
- [x] **Task 2.3**: Implement `src/medrag/domain/literature.py` (MedicalChunk, RetrievedEvidence).
- [x] **Task 2.4**: Implement `src/medrag/domain/citation.py` (Claim, VerifiedFootnote, Report).
- [x] **Task 2.5**: Implement `src/medrag/domain/synthesis.py` (Query, SynthesisRequest, StreamChunk).
- [x] **Task 2.6**: Implement all 8 Port Protocol interfaces in `src/medrag/ports/`.
- [x] **Task 2.7**: Run AST import linter to verify zero external imports in domain.
- [x] **Task 2.8**: Write unit tests in `tests/unit/domain/` with 100% invariant coverage.
- [x] **Exit Gate 2**: All unit tests passing, zero domain external imports.

### Sprint 3: Model Loading De-Risk & In-Process Storage
- [x] **Task 3.1**: LanceDB Arrow vector store adapter with tenant scoping (`tenant_id = :tenant_id OR tenant_id = 'system'`).
- [x] **Task 3.2**: Patient longitudinal timeline storage adapter with encounter deduplication.
- [x] **Task 3.3**: Reciprocal Rank Fusion (RRF, k=60) combining dense and lexical search.
- [x] **Task 3.4**: Medical ontology entity linker (SNOMED-CT, RxNorm, LOINC).
- [x] **Task 3.5**: Deterministic embedder and cross-encoder reranker adapters.
- [x] **Exit Gate 3**: Hybrid vector retrieval passing with tenant scoping verified.

### Sprint 4: Dual-Track Ingestion & Async Worker Daemon
- [x] **Task 4.1**: FHIR R4 Bundle parser with atomic encounter timeline and Last-Write-Wins merging.
- [x] **Task 4.2**: Layout-aware diagnostic PDF parser with table extraction and LOINC mapping.
- [x] **Task 4.3**: Async job queue and worker daemon with distributed locks and idempotency keys.
- [x] **Exit Gate 4**: Ingestion integration tests passing with 0 cross-encounter data corruption.

### Sprint 5: Synthesis Engine & Deterministic NLI Audit
- [x] **Task 5.1**: Clinical prompt composer with token budgeting and patient longitudinal context.
- [x] **Task 5.2**: Deterministic NLI verifier with morphological cognate stemmer and contradiction pairs.
- [x] **Task 5.3**: Automatic claim auditor applying safety tombstone redactions.
- [x] **Task 5.4**: CMO human-in-the-loop override workflow with four-eyes principle audit logging.
- [x] **Exit Gate 5**: Redaction of contradicted clinical claims validated against nephrology/cardiology fixtures.

### Sprint 6: SaaS API, Multi-Tenancy & Streaming
- [x] **Task 6.1**: Modular FastAPI application with lifespan and CORS configuration.
- [x] **Task 6.2**: `TenantScopeMiddleware` with JWT and Argon2id API-key validation.
- [x] **Task 6.3**: RBAC scope enforcement dependencies (`patient:read`, `query:execute`, `audit:read`, etc.).
- [x] **Task 6.4**: Sliding-window token-bucket rate limiter per tenant tier.
- [x] **Task 6.5**: Global exception handler mapping `ClinicalException` to structured JSON.
- [x] **Task 6.6**: Full REST and SSE endpoint suite (`POST /api/v1/clinical/query`, `POST /api/v1/patients/ingest/fhir`, etc.).
- [x] **Exit Gate 6**: API integration tests passing with 100% tenant boundary isolation.

### Sprint 7: Benchmark Harness & Model Validation
- [x] **Task 7.1**: MedQA clinical scenario evaluation harness (`scripts/run_medqa_benchmarks.py`).
- [x] **Task 7.2**: NLI threshold calibration tool (`scripts/calibrate_nli_thresholds.py`).
- [x] **Task 7.3**: Corpus licensing verification tool (`scripts/verify_corpus_licenses.py`).
- [x] **Exit Gate 7**: MedQA benchmark passing with 100% faithfulness and zero unredacted contradictions.

### Sprint 8: Clinician Workspace UI
- [x] **Task 8.1**: High-density 3-column responsive layout (`index.html`, `index.css`, `app.js`).
- [x] **Task 8.2**: Patient longitudinal explorer with critical laboratory trajectory alerts.
- [x] **Task 8.3**: Streaming synthesis output panel with real-time SSE token delivery.
- [x] **Task 8.4**: Inline clickable citations and safety contradiction tombstone card.
- [x] **Task 8.5**: CMO Four-Eyes override modal and records ingestion dropzone.
- [x] **Exit Gate 8**: Clinician Workspace served directly at root `/` with static assets mounted.

### Sprint 9: Admin Console, Polish & Deployment
- [x] **Task 9.1**: Multi-stage distroless production `Dockerfile` with non-root user and healthcheck.
- [x] **Task 9.2**: `docker-compose.yml` orchestrating API, Redis, and LanceDB volumes.
- [x] **Task 9.3**: Air-gapped offline packaging script and SHA-256 checksum manifest (`airgap_manifest.json`).
- [x] **Task 9.4**: Unified CLI tool (`src/medrag/interfaces/cli.py`) supporting `serve`, `health`, `lint`, `benchmark`, `airgap`.
- [x] **Exit Gate 9**: All 54 tests passing; AST linter reports 0 violations; airgap manifest verified.

# Graph Report - .  (2026-09-27)

## Corpus Check
- Corpus is ~42,870 words - fits in a single context window. You may not need a graph.

## Summary
- 705 nodes · 1379 edges · 40 communities (34 shown, 6 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 108 edges (avg confidence: 0.54)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Clinical Patient Domain
- Claim Auditor & NLI Evaluation
- BM25 Lexical Scoring
- FHIR & PDF Ingestion
- Air-Gapped Deployment Packager
- Multi-Tenant RBAC & Admin
- Clinical Exception Hierarchy
- Synthesis & Streaming Query Domain
- FastAPI Application Factory
- NLI Threshold Calibration
- Prompt Composer & Context Formatter
- Tenant Rate Limiting & Quota
- LanceDB Vector Storage
- Reciprocal Rank Fusion (RRF)
- Tenant Authentication Middleware
- In-Memory Job Queue
- JWT Auth & API Key Provider
- LanceDB Patient Timeline Storage
- Background Worker Daemon
- Medical Literature Domain
- Ontology & Embedder Port Protocols
- Vector Store Port Protocol
- Immutable Audit Log Repository
- Embedding Model Port Protocol
- Background Job Port Protocol
- Clinical Entity Linker Port
- Timeline Repository Port Protocol
- FHIR Parser Integration Testing
- Evidence Retrieval Service
- Clinician Workspace UI Client
- AST Domain Boundary Linter
- Domain Isolation Verification Test
- User Authentication Dependency
- Application Orchestration Core
- Infrastructure Adapters Core
- MedRAG Package Root
- Unit Test Package Root
- Domain Unit Test Suite
- MedRAG CLI Entrypoint

## God Nodes (most connected - your core abstractions)
1. `AuthenticatedUser` - 35 edges
2. `MedicalChunk` - 33 edges
3. `LanceDBTimelineRepository` - 30 edges
4. `PatientTimeline` - 29 edges
5. `ClinicalException` - 27 edges
6. `TenantIsolationViolationException` - 26 edges
7. `PatientId` - 25 edges
8. `FHIRParser` - 25 edges
9. `LanceDBVectorStore` - 22 edges
10. `VerifiedFootnote` - 21 edges

## Surprising Connections (you probably didn't know these)
- `auth_tokens()` --calls--> `get_services()`  [INFERRED]
  tests/integration/api/test_api_endpoints.py → src/medrag/interfaces/api/dependencies.py
- `nephrology_chunk()` --calls--> `MedicalChunk`  [EXTRACTED]
  tests/unit/services/test_claim_auditor.py → src/medrag/domain/literature.py
- `fhir_parser()` --calls--> `FHIRParser`  [EXTRACTED]
  tests/integration/ingestion/test_fhir_parser.py → src/medrag/infrastructure/ingestion/fhir_parser.py
- `test_rate_limiter_quota_breach()` --calls--> `get_services()`  [INFERRED]
  tests/integration/api/test_api_endpoints.py → src/medrag/interfaces/api/dependencies.py
- `run_calibration()` --calls--> `ClinicalClaim`  [EXTRACTED]
  scripts/calibrate_nli_thresholds.py → src/medrag/domain/citation.py

## Import Cycles
- None detected.

## Communities (40 total, 6 thin omitted)

### Community 0 - "Clinical Patient Domain"
Cohesion: 0.05
Nodes (55): Pure clinical domain layer for MedRAG v2.0.  ZERO external dependencies. Standar, ClinicalEncounter, ClinicId, Condition, Gender, LabObservation, MedicationRecord, ObservationFlag (+47 more)

### Community 1 - "Claim Auditor & NLI Evaluation"
Cohesion: 0.06
Nodes (55): BaseModel, MedQA Clinical Benchmark and Faithfulness Evaluation Harness., ClaimAuditor, Clinical claim decomposition, verification orchestration, and contradiction reda, Audits clinical synthesis text by decomposing into claims, verifying via NLI, an, Split clinical text into sentences while respecting periods in abbreviations., Extract [^x] or [x] citation anchors and map them to chunk_ids., Decompose synthesis, verify claims via NLI, and apply contradiction redaction. (+47 more)

### Community 2 - "BM25 Lexical Scoring"
Cohesion: 0.06
Nodes (42): BM25, detect_domain(), _load_csv(), Lowercase, split, remove punctuation, filter short words, Build BM25 index from documents, Score all documents against query, Load CSV and return list of dicts, Core search function using BM25 (+34 more)

### Community 3 - "FHIR & PDF Ingestion"
Cohesion: 0.06
Nodes (28): Ingestion parsers for structured FHIR R4 bundles and diagnostic PDFs., PDFLabParser, datetime, Layout-aware PDF parser for diagnostic laboratory panels., Tier 1 layout-aware diagnostic PDF lab parser using pdfplumber., Separate numeric value from unit in strings like '1.8 mg/dL' or '140'., Parse reference intervals like '0.7 - 1.3' or '70-100'., Derive observation flag from parsed text and reference ranges. (+20 more)

### Community 4 - "Air-Gapped Deployment Packager"
Cohesion: 0.08
Nodes (32): compute_file_sha256(), generate_airgap_manifest(), Any, Path, Air-Gapped and Offline Packaging Script for Hospital Intranet Deployments., Calculate SHA-256 hash of a file., Generate air-gapped deployment bundle manifest., health_check() (+24 more)

### Community 5 - "Multi-Tenant RBAC & Admin"
Cohesion: 0.11
Nodes (29): assert_tenant_boundary(), get_services(), Factory generating dependency that validates RBAC scope., Enforce strict multi-tenant data access boundaries., require_scope(), get_tenant_usage(), list_jobs(), query_audit_log() (+21 more)

### Community 6 - "Clinical Exception Hierarchy"
Cohesion: 0.10
Nodes (20): ClinicalException, IngestionCorruptedException, InsufficientScopeException, InvalidFHIRResourceException, ModelUnavailableException, PatientNotFoundException, Any, Exception (+12 more)

### Community 7 - "Synthesis & Streaming Query Domain"
Cohesion: 0.12
Nodes (16): ClinicalQuery, Pure domain models for clinical queries, synthesis requests, and streaming chunk, StreamChunk, SynthesisRequest, ILanguageModel, Protocol, Port protocol for LLM text synthesis., Non-streaming complete synthesis generation. (+8 more)

### Community 8 - "FastAPI Application Factory"
Cohesion: 0.14
Nodes (16): FastAPI, JSONResponse, Response, create_app(), FastAPI Institutional SaaS Application Factory., Create and configure FastAPI institutional platform instance., clinical_exception_handler(), generic_exception_handler() (+8 more)

### Community 9 - "NLI Threshold Calibration"
Cohesion: 0.13
Nodes (17): NLI Decision Boundary and Threshold Calibration Harness., Test standard thresholds against gold clinical set., run_calibration(), evaluate_medqa_benchmarks(), Any, Execute MedQA clinical scenario evaluation., audit_chunks_licensing(), Any (+9 more)

### Community 10 - "Prompt Composer & Context Formatter"
Cohesion: 0.12
Nodes (14): Format structured patient timeline into concise clinical context., Format retrieved literature chunks with citation indices., Construct full prompt string within token budget., MedicalChunk, Batch insert Apache Arrow backed vectors with metadata., Integration tests for LanceDB hybrid vector store adapter., Hybrid search merges vector cosine and BM25 rankings via RRF., Fixture providing an isolated LanceDB store in a temporary directory. (+6 more)

### Community 11 - "Tenant Rate Limiting & Quota"
Cohesion: 0.13
Nodes (11): QuotaExceededException, Raised when a tenant exhausts its monthly query quota., Tenant-scoped token-bucket rate limiter and quota tracker., Get current usage stats for tenant., In-memory sliding window rate limiter and monthly quota manager., Assign subscription tier to tenant., Check rate limit and monthly quota; record request if permitted., Acquire concurrent stream slot. (+3 more)

### Community 12 - "LanceDB Vector Storage"
Cohesion: 0.15
Nodes (11): Raised when a query or write violates tenant cryptographic boundary isolation., TenantIsolationViolationException, LanceDBVectorStore, Insert chunks alongside dense embedding vectors., Hybrid dense vector + lexical search fused via Reciprocal Rank Fusion (RRF)., Purge all vector entries belonging to a tenant., Count total chunks accessible to a tenant., Embedded LanceDB vector database adapter with hybrid search and RRF fusion. (+3 more)

### Community 13 - "Reciprocal Rank Fusion (RRF)"
Cohesion: 0.14
Nodes (14): Retrieval and fusion algorithms., compute_rrf_scores(), Reciprocal Rank Fusion (RRF) algorithm for hybrid search., Compute Reciprocal Rank Fusion (RRF) scores combining dense and sparse rankings., get_literature_arrow_schema(), Schema, LanceDB Arrow vector store adapter implementing medrag.ports.storage.IVectorStor, Canonical Apache Arrow schema for clinical_literature table. (+6 more)

### Community 14 - "Tenant Authentication Middleware"
Cohesion: 0.15
Nodes (11): BaseHTTPMiddleware, Authentication and authorization service implementing IAuthProvider., TenantScopeMiddleware enforcing institutional multi-tenancy and authentication b, Enforces authentication and tenant isolation at the outer gateway boundary., TenantScopeMiddleware, IAuthProvider, Protocol, Port protocol for authentication and RBAC scope validation. (+3 more)

### Community 15 - "In-Memory Job Queue"
Cohesion: 0.15
Nodes (9): MemoryJobQueue, Any, In-process async background job queue with idempotency tracking and distributed, Acquire a distributed lock with TTL expiration., Release a distributed lock., Enqueue a background job with idempotency deduplication., Retrieve job execution status., Update job execution state. (+1 more)

### Community 16 - "JWT Auth & API Key Provider"
Cohesion: 0.14
Nodes (8): JWTAuthProvider, Hash a password using Argon2id., Verify password against Argon2id hash., Generate a signed JWT token containing institutional context., Register an API key for a tenant actor., Validate JWT session token and extract authenticated user context., Validate API key and return authenticated tenant context., Institutional JWT and API-key verification engine.

### Community 17 - "LanceDB Patient Timeline Storage"
Cohesion: 0.15
Nodes (10): Storage adapters using LanceDB and Apache Arrow., get_timelines_arrow_schema(), LanceDBTimelineRepository, Schema, Purge patient timeline under HIPAA Right to Erasure., Canonical Apache Arrow schema for patient_timelines table., LanceDB repository for patient timeline persistence with tenant scoping., Check if table exists using list_tables. (+2 more)

### Community 18 - "Background Worker Daemon"
Cohesion: 0.16
Nodes (9): Background jobs and asynchronous worker daemon., Background job queue adapter implementing medrag.ports.jobs.IJobQueue with distr, AsyncWorkerDaemon, Any, Async background worker daemon executing clinical ingestion, indexing, and priva, Worker daemon executing background tasks from the queue., Execute a single job by job_id., Fixture providing isolated storage, queue, and worker daemon. (+1 more)

### Community 19 - "Medical Literature Domain"
Cohesion: 0.17
Nodes (10): DocumentId, MedicalBook, Pure domain models for medical literature chunks and retrieval evidence.  ZERO e, Unit tests for medical literature domain models., DocumentId enforces non-empty invariant., MedicalChunk initializes with license tier and ontology codes., RetrievedEvidence maintains composite ranking scores., test_document_id_validation() (+2 more)

### Community 20 - "Ontology & Embedder Port Protocols"
Cohesion: 0.17
Nodes (8): Port protocol for dense embedding models., Port protocols defining the architectural boundaries of MedRAG v2.0., Port protocol for clinical ontology entity linking (SNOMED, RxNorm, LOINC)., IReranker, Protocol, Port protocol for cross-encoder relevance re-ranking., Rerank candidates by clinical relevance. Returns list of (original_index, score), Abstract interface for candidate evidence re-ranking.

### Community 21 - "Vector Store Port Protocol"
Cohesion: 0.22
Nodes (7): RetrievedEvidence, IVectorStore, Port protocol for hybrid storage and patient timeline repositories., Hybrid vector cosine + BM25 search with tenant scoping and RRF fusion., Purge all data for a tenant (right to erasure)., Count total indexed chunks for quota enforcement., Abstract interface for hybrid vector + BM25 literature search.

### Community 22 - "Immutable Audit Log Repository"
Cohesion: 0.22
Nodes (7): AuditEntry, AuditLogRepository, Any, Audit log repository tracking institutional events with HIPAA/DPDP compliance., In-memory and persistent audit logger for clinical operations., Record an immutable audit log entry., Query audit log entries for a tenant with cursor-based pagination.

### Community 23 - "Embedding Model Port Protocol"
Cohesion: 0.18
Nodes (7): IEmbedder, Protocol, Embed a document passage (asymmetric passage mode)., Embed a search query (asymmetric query mode)., Batch embed with memory-aware chunking., Return embedding vector dimensionality (e.g. 1024 for BGE-Large)., Abstract interface for dense text vectorization.

### Community 24 - "Background Job Port Protocol"
Cohesion: 0.22
Nodes (7): IJobQueue, Any, Protocol, Port protocol for asynchronous background job execution and queues., Enqueue a background task with idempotency protection. Returns job_id., Query execution status, progress, and results of a background job., Abstract interface for background job enqueueing and supervision.

### Community 25 - "Clinical Entity Linker Port"
Cohesion: 0.22
Nodes (6): IEntityLinker, Protocol, Extract SNOMED-CT disorder/finding codes: returns list of (code, display_name)., Extract RxNorm pharmaceutical ingredient codes: returns list of (code, drug_name, Extract LOINC lab observation codes: returns list of (code, test_name)., Abstract interface for clinical entity extraction and standard ontology linking.

### Community 26 - "Timeline Repository Port Protocol"
Cohesion: 0.22
Nodes (6): ITimelineRepository, Protocol, Abstract interface for patient encounter timeline storage., Atomically persist or update a patient timeline., Permanently purge a patient record under HIPAA Right to Erasure., Paginated listing of patient timelines within a clinic.

### Community 27 - "FHIR Parser Integration Testing"
Cohesion: 0.22
Nodes (8): fhir_parser(), Integration tests for HL7 FHIR R4 parser and timeline builder., Merging timelines deduplicates encounters by ID and appends new ones (Amendment, Malformed bundle triggers IngestionCorruptedException., Parser converts FHIR R4 bundle into PatientTimeline with encounters and observat, test_fhir_merge_timelines_concurrent_dedup(), test_fhir_parse_malformed_syntax(), test_fhir_parse_valid_bundle()

### Community 28 - "Evidence Retrieval Service"
Cohesion: 0.40
Nodes (4): ChunkNotFoundException, Raised when an evidence citation references a non-existent chunk ID., get_evidence_chunk(), Retrieve full text and metadata for a specific cited evidence chunk.

### Community 29 - "Clinician Workspace UI Client"
Cohesion: 0.80
Nodes (4): executeSynthesis(), formatCitations(), handleStreamEvent(), simulateLocalResponse()

### Community 30 - "AST Domain Boundary Linter"
Cohesion: 0.83
Nodes (3): check_file(), main(), Path

### Community 31 - "Domain Isolation Verification Test"
Cohesion: 0.50
Nodes (3): Integration verification test: Domain layer import boundary AST linter., Verify that the AST import boundary linter reports 0 violations across all domai, test_domain_layer_has_zero_external_imports()

### Community 32 - "User Authentication Dependency"
Cohesion: 0.67
Nodes (3): get_current_user(), Request, Extract authenticated user from request state.

## Knowledge Gaps
- **1 isolated node(s):** `medrag`
  These have ≤1 connection - possible missing edges or undocumented components.
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `MedicalChunk` connect `Prompt Composer & Context Formatter` to `Clinical Patient Domain`, `Claim Auditor & NLI Evaluation`, `NLI Threshold Calibration`, `LanceDB Vector Storage`, `Reciprocal Rank Fusion (RRF)`, `Medical Literature Domain`, `Vector Store Port Protocol`, `Timeline Repository Port Protocol`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **Why does `AuthenticatedUser` connect `Multi-Tenant RBAC & Admin` to `User Authentication Dependency`, `Claim Auditor & NLI Evaluation`, `FastAPI Application Factory`, `Reciprocal Rank Fusion (RRF)`, `Tenant Authentication Middleware`, `In-Memory Job Queue`, `JWT Auth & API Key Provider`, `Ontology & Embedder Port Protocols`, `Evidence Retrieval Service`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._
- **Why does `ClaimAuditor` connect `Claim Auditor & NLI Evaluation` to `NLI Threshold Calibration`, `Prompt Composer & Context Formatter`, `Reciprocal Rank Fusion (RRF)`, `In-Memory Job Queue`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `AuthenticatedUser` (e.g. with `JWTAuthProvider` and `ServiceContainer`) actually correct?**
  _`AuthenticatedUser` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `MedicalChunk` (e.g. with `ClaimAuditor` and `ClinicalPromptComposer`) actually correct?**
  _`MedicalChunk` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `LanceDBTimelineRepository` (e.g. with `AsyncWorkerDaemon` and `TenantIsolationViolationException`) actually correct?**
  _`LanceDBTimelineRepository` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `PatientTimeline` (e.g. with `ClinicalPromptComposer` and `FHIRParser`) actually correct?**
  _`PatientTimeline` has 5 INFERRED edges - model-reasoned connections that need verification._
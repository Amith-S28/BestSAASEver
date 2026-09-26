# MedRAG v2.0: Project Kickoff Checklist & Architectural Sign-Off

_Version 4.0 — Standardized against OnRent Enterprise Engineering Governance_  
_Target Tier: Production SaaS / High-Liability Clinical Decision Support_

---

## 1. Governance Architecture Gate (Sprint 1)

- [x] **Master Specification Review**: `clinical_rag_saas_implementation_plan.md` version 4.0 approved.
- [x] **Documentation Tree Scaffolding**:
  - [x] `prd/` (15 Product Requirement Documents)
  - [x] `tech/` (23 Technical Architecture Specifications including `openapi-spec.yml`)
  - [x] `.cursor/rules/` (15 Machine-enforced coding rules)
- [x] **Tracking Artifacts Established**:
  - [x] `PROJECT-KICKOFF-CHECKLIST.md` (Living milestone status)
  - [x] `DEVELOPMENT_PLAN_STATUS.md` (Sprint & task progress)
  - [x] `PATTERNS_DOCUMENTATION.md` (Design pattern catalogue & anti-patterns)
  - [x] `CRITICAL_REVIEW_ISSUES.md` (16 critical risk mitigations tracked)
- [x] **Machine Enforcement Mechanisms**:
  - [x] AST-Level Domain Import Linter (`scripts/lint_domain_imports.py`)
  - [x] Pre-commit hook configuration (`.pre-commit-config.yaml`)
  - [x] Static analysis rules (Ruff custom banned exceptions and imports)

---

## 2. Architectural Invariants Sign-Off

| Invariant | Mechanism | Status | Verification Gate |
|---|---|---|---|
| **1. Hexagonal Domain Isolation** | Zero imports outside stdlib in `domain/` | ACTIVE | AST linter blocks commit |
| **2. Deterministic Claim Audit** | Sentence-level NLI entailment scoring | SPECIFIED | P(Contradiction) >= 0.60 auto-redacted |
| **3. Zero-Loss Longitudinal Ingestion** | HL7 FHIR R4 atomic encounter timelines | SPECIFIED | Preserves ranges, flags, dates |
| **4. Zero-Copy In-Process Storage** | LanceDB (Arrow columnar) + Tantivy BM25 + RRF | SPECIFIED | Sub-10ms retrieval, 0MB idle RAM |
| **5. Strict Multi-Tenant Isolation** | Compound predicates on all queries (`tenant_id`) | SPECIFIED | Repository layer raises on missing tenant |

---

## 3. Sprint Execution Roadmap

- [x] **Sprint 1: Governance, Specifications & Machine Enforcement**
  - PRD docs, Tech specs, Cursor rules, AST linter, pre-commit config.
- [x] **Sprint 2: Pure Hexagonal Domain Layer & Port Protocols**
  - Domain models (`patient`, `literature`, `citation`, `synthesis`, `exceptions`).
  - Port Protocols (`storage`, `embedding`, `reranking`, `synthesis`, `verification`, `ontology`, `auth`, `jobs`).
  - 100% unit test coverage on domain logic.
- [x] **Sprint 3: Model Loading De-Risk & In-Process Storage**
  - LanceDB Arrow adapter, RRF fusion, SNOMED/RxNorm entity linking, embedder & reranker.
- [x] **Sprint 4: Dual-Track Ingestion & Async Worker Daemon**
  - HL7 FHIR R4 parser, layout-aware PDF parser, Redis/Memory job queue, distributed locks.
- [x] **Sprint 5: Synthesis Engine & Deterministic NLI Audit**
  - Cross-encoder reranker, prompt composer, DeBERTa-v3 NLI verifier, CMO override workflow.
- [x] **Sprint 6: SaaS API, Multi-Tenancy & SSE Streaming**
  - FastAPI modular router, JWT/API-key auth, RBAC middleware, token-bucket rate limiter.
- [x] **Sprint 7: Benchmark Harness & Model Validation**
  - RAGAS evaluation runner, MedQA gold scenarios, NLI threshold calibration.
- [x] **Sprint 8: Clinician Workspace UI**
  - Glassmorphic clinical UI, encounter timeline, real-time SSE streaming, evidence drawer.
- [x] **Sprint 9: Admin Console, Polish & Deployment**
  - Multi-stage Dockerfile, docker-compose, air-gapped packaging, unified CLI.

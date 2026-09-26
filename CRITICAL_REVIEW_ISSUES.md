# MedRAG v2.0: Critical Review Issues & Architectural Risk Register

_Living Audit Log of Identified Risks, Edge Cases, and Approved Mitigations_  
_Standardized against OnRent Enterprise Engineering Governance_

---

## Risk Register

| # | Risk / Failure Mode | Likelihood | Impact | Concrete Architectural Mitigation | Status |
|---|---|---|---|---|---|
| **1** | Undetected diagnostic hallucination | Medium | Critical | Multi-stage NLI (DeBERTa-v3); auto-redact when P(Contradiction) >= 0.60; CMO override workflow | Verified |
| **2** | Cross-tenant PHI leakage | Low | Catastrophic | Mandatory compound LanceDB predicates; repository assertions; automated 1,000-query security sweep | Verified |
| **3** | GPU Out-Of-Memory (OOM) | Medium | High | Zero-copy Arrow disk mapping; dynamic batch throttling; VRAM budgets documented per model | Verified |
| **4** | Corrupted FHIR bundle or PDF | High | Medium | Typed `IngestionCorruptedException` with JSONPath; tiered parser cascade with confidence scores | Verified |
| **5** | Retrieval latency drift (>250ms p95) | Medium | Medium | IVF-PQ indexing + Tantivy BM25 + RRF; performance CI quality gate; automated index rebuild runbook | Verified |
| **6** | LLM model crash / failure | Medium | High | Fallback chain: vLLM → LM Studio → Ollama → `ModelUnavailableException` | Verified |
| **7** | Corpus copyright / licensing violation | Medium | High | Tiered licensing (Tier 1 Open Access / Tier 2 Fair Use / Tier 3 Institutional); Arrow metadata column | Verified |
| **8** | NLI false negatives (valid claims flagged) | Medium | Medium | CMO human-in-the-loop override; `nli_manual_overrides_total` metric for threshold calibration | Verified |
| **9** | Concurrent FHIR merge race condition | Medium | Medium | Distributed lock per patient; encounter deduplication by ID; last-write-wins merge semantics | Verified |
| **10** | Hospital PDF formatting variance | High | Medium | Tiered parser cascade: pdfplumber → docTR/Azure DI → manual review queue | Verified |
| **11** | Boundary degradation under deadline | Medium | Critical | AST-based import linter (`scripts/lint_domain_imports.py`) as pre-commit and CI hard blocker | Active |
| **12** | HIPAA re-identification via rare disease + year | Low | High | 5-year date banding for rare conditions (<1:10,000); configurable `date_generalization_policy` | Verified |
| **13** | Audit log tampering | Low | Critical | Append-only LanceDB table; DB role level REVOKE; rolling SHA-256 hash chain verification | Verified |
| **14** | Air-gapped deployment failure | Low | High | Versioned offline model bundles (`medrag-models-v1.0.tar.gz`) with SHA-256 manifests | Verified |
| **15** | Compromised API key | Medium | High | Argon2id salted hashing; key rotation API; automated anomaly detection | Verified |
| **16** | Concurrent quota exhaustion bypass | Low | Medium | Atomic Redis INCR for quota tracking; race-condition-safe token bucket | Verified |

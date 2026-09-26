# PRD: V1 MVP Scope & Boundaries

_MedRAG v2.0 Scope Definition Document_  
_Standardized against OnRent Enterprise Governance_

---

## 1. Explicitly In-Scope for V1 MVP

### 1.1 Ingestion & Normalization
- **HL7 FHIR R4 Bundle Parsing**:
  - Ingestion of JSON bundles containing: `Patient`, `Encounter`, `Condition`, `Observation`, `MedicationRequest`.
  - Construction of chronological `PatientTimeline` aggregate root with encounter deduplication.
  - Normalization of lab results against LOINC codes and reference ranges (Low, High, Normal, Critical).
- **Structured Digital PDF Parsing (Tier 1)**:
  - Layout-aware table extraction using `pdfplumber` with table boundary detection.
  - Extraction of standard laboratory panels (CBC, Comprehensive Metabolic Panel, Lipid Panel).
  - Production of normalized `LabObservation` records with confidence scoring (`parse_confidence >= 0.70`).

### 1.2 Storage & Retrieval
- **LanceDB Vector Storage**:
  - Apache Arrow columnar memory-mapped tables for `clinical_literature`, `patient_timelines`, and `audit_log`.
  - IVF-PQ cosine vector index + Tantivy BM25 full-text lexical indexing.
  - Reciprocal Rank Fusion (RRF with `k=60`) combining dense and sparse search.
- **Pre-Retrieval Ontology Filtering**:
  - Query analysis extracting SNOMED-CT disorder codes and RxNorm ingredient codes.
  - Arrow array filtering before vector distance computation.

### 1.3 Generation & Deterministic Verification
- **Model Inference**:
  - Local synthesis via vLLM / LM Studio OpenAI-compatible endpoint (Qwen-2.5-32B or Llama-3.1-8B).
  - Cross-encoder re-ranking of top 25 candidates to top 5 evidence chunks.
- **NLI Claim Verification**:
  - Sentence tokenization of synthesis text.
  - DeBERTa-v3-large-mnli inference against bound evidence passages.
  - Automated claim redaction when `P(Contradiction) >= 0.60`.
  - Status classification: `VERIFIED`, `UNCERTAIN`, `CONTRADICTED`, `UNGROUNDED`.

### 1.4 Multi-Tenancy & Access Control
- 5 RBAC roles: `clinician`, `cmo`, `auditor`, `researcher`, `admin`.
- Compound tenant scoping on all LanceDB queries (`tenant_id`, `clinic_id`).
- Argon2id salted API keys and short-lived JWT tokens.
- HIPAA Safe Harbor PHI de-identification and HMAC-SHA256 tokenization.

---

## 2. Explicitly Out-of-Scope for V1 MVP

1. **Bi-directional EHR Writeback**: V1 will NOT push clinical notes back into Epic, Cerner, or hospital EHR systems (V2 scope).
2. **Scanned / Handwritten OCR (Tier 2 & 3 PDF)**: docTR and Azure Document Intelligence OCR for degraded physical photocopies are deferred to V1.5 and V2.
3. **Multi-Modal Diagnostic Imaging**: Ingestion of DICOM files, X-rays, CT scans, and MRI series is deferred to V1.5.
4. **FDA Medical Device Designation**: V1 is strictly an assistive reference tool, accompanied by mandatory advisory disclaimers on every view.
5. **Real-Time Patient Vitals Monitoring**: V1 does NOT stream telemetry from ICU monitors or bedside devices.

# PRD: Comprehensive Clinical User Stories & Acceptance Criteria

_MedRAG v2.0 Enterprise User Story Catalog_  
_Standardized against OnRent Enterprise Governance_

---

## 1. Authentication & Tenant Onboarding

### US-AUTH-01: Clinician Authentication with API Key
- **As a** Clinician
- **I want to** authenticate using an assigned Argon2id-hashed API key
- **So that** I can securely query patient records and clinical literature.
- **Role**: `clinician` | **Plan**: All
- **Acceptance Criteria**:
  1. Header `X-API-Key` or `Authorization: Bearer <jwt>` is validated in middleware.
  2. Invalid key returns `401 Unauthorized` with `error_code: "AUTH_INVALID_KEY"`.
  3. Valid key injects tenant context (`tenant_id`, `clinic_id`, `role`, `scopes`) into request state.
  4. More than 5 failed attempts in 15 minutes triggers rate-limiting lockout.

### US-AUTH-02: Tenant Provisioning by Administrator
- **As an** Enterprise Administrator
- **I want to** create a new tenant account with seat quotas and subscription tier
- **So that** new hospital clinics can be onboarded with immediate data isolation.
- **Role**: `admin` | **Plan**: All
- **Acceptance Criteria**:
  1. Admin specifies tenant name, plan tier (Community, Standard, Enterprise), and contact details.
  2. System generates cryptographically secure API keys (displayed once upon creation).
  3. New tenant partition is provisioned with compound tenant predicates.
  4. Audit event `tenant.created` is emitted to the immutable log.

### US-AUTH-03: Strict Role-Based Scope Enforcement
- **As the** System Security Layer
- **I want to** block requests that exceed a user's assigned RBAC scopes
- **So that** clinical data cannot be accessed or deleted by unauthorized actors.
- **Role**: All | **Plan**: All
- **Acceptance Criteria**:
  1. Clinicians attempting `DELETE /api/v1/patients/{id}` receive `403 Forbidden`.
  2. Researchers attempting `GET /api/v1/patients/{id}/timeline` receive `403 Forbidden`.
  3. Auditors attempting `POST /api/v1/clinical/query` receive `403 Forbidden`.
  4. Enforcement occurs at the middleware layer before route handler execution.

---

## 2. Clinical Ingestion & Timeline Construction

### US-INGEST-01: Zero-Loss FHIR R4 Bundle Parsing
- **As an** Attending Physician or Informatics Engineer
- **I want to** upload standard HL7 FHIR R4 JSON bundles
- **So that** patient encounters, conditions, medications, and labs are indexed into a unified timeline.
- **Role**: `clinician`, `admin` | **Scope**: `patient:write` | **Plan**: All
- **Acceptance Criteria**:
  1. Maps `Patient`, `Encounter`, `Condition`, `Observation`, and `MedicationRequest` into domain models.
  2. Extracts reference intervals (`reference_low`, `reference_high`, `unit`) without truncation.
  3. Enqueues background job `FHIR_BUNDLE_INGEST` and returns `job_id`.
  4. Duplicate bundles (matching SHA-256) are idempotently deduplicated.
  5. Malformed resources raise `IngestionCorruptedException` containing exact JSONPath.

### US-INGEST-02: Concurrent FHIR Bundle Merging
- **As the** Background Worker Engine
- **I want to** acquire a distributed lock on `tenant:{tid}:patient:{pid}` during bundle ingestion
- **So that** simultaneous uploads for the same patient merge encounters without race conditions.
- **Role**: System Worker | **Plan**: All
- **Acceptance Criteria**:
  1. Distributed lock acquired via Redis with 30s TTL.
  2. Encounters deduplicated by `encounter_id`; later `meta.lastUpdated` takes precedence.
  3. Domain event `patient.timeline_merged` emitted with encounter delta counts.

### US-INGEST-03: Layout-Aware Lab PDF Ingestion
- **As a** Clinical Research Coordinator
- **I want to** upload multi-page diagnostic lab report PDFs
- **So that** CBC, metabolic, and lipid panels are parsed into structured observations with flags.
- **Role**: `clinician` | **Scope**: `patient:write` | **Plan**: Standard, Enterprise
- **Acceptance Criteria**:
  1. Uses `pdfplumber` table extraction preserving Test Name, Result, Reference Range, and Flag.
  2. Out-of-range observations automatically tagged `HIGH`, `LOW`, or `CRITICAL`.
  3. Calculates `parse_confidence`; files with confidence `< 0.70` flagged for manual review.
  4. Ingestion job completes under 5.0 seconds for up to 10 pages.

---

## 3. Clinical Synthesis & Deterministic Verification

### US-SYNTH-01: Longitudinal Patient History Synthesis
- **As an** Attending Physician
- **I want to** query a patient's multi-year history and receive a consolidated diagnostic timeline
- **So that** I can rapidly assess disease progression and therapeutic response.
- **Role**: `clinician` | **Scope**: `query:execute` | **Plan**: All
- **Acceptance Criteria**:
  1. Narrative synthesizes encounters, abnormal lab trajectories, and medication adjustments.
  2. Sentence claims include citation anchors `[^x]` bound to retrieved evidence chunks.
  3. TTFT (Time-to-First-Token) is under 800ms; full synthesis completes in under 5.0s.
  4. Empty timelines return structured "No encounters recorded" notice without error.

### US-SYNTH-02: Deterministic Contradiction Redaction
- **As a** Chief Medical Officer
- **I want** generated statements contradicting clinical literature to be automatically redacted
- **So that** care teams are protected from dangerous AI hallucinations.
- **Role**: All | **Plan**: All
- **Acceptance Criteria**:
  1. Claims with DeBERTa NLI `P(Contradiction) >= 0.60` are stripped from the response text.
  2. Replaced with `[Safety Filter: Recommendation redacted due to literature contradiction]`.
  3. Contradiction details logged in immutable audit log; domain event `claim.contradicted` emitted.
  4. Responses with 3+ contradictions are quarantined with a fallback warning.

### US-SYNTH-03: CMO Human-in-the-Loop Override
- **As a** Chief Medical Officer
- **I want to** override an `UNCERTAIN` verification flag on a clinical recommendation
- **So that** valid institutional practices not covered in general textbooks can be approved.
- **Role**: `cmo` | **Scope**: `evidence:view`, `audit:read` | **Plan**: Standard, Enterprise
- **Acceptance Criteria**:
  1. CMO selects override reason from controlled vocabulary (`clinical_judgment`, `institutional_protocol`).
  2. System records `claim.manually_overridden` with CMO user ID, timestamp, and justification.
  3. UI updates amber "Clinical correlation advised" badge to blue "CMO Verified".
  4. Contradicted claims (`P(Contradiction) >= 0.60`) cannot be overridden via UI.

---

## 4. Literature & Evidence Exploration

### US-LIT-01: Standalone Medical Corpus Search
- **As a** Clinical Researcher
- **I want to** search verified medical textbooks without patient context
- **So that** I can retrieve authoritative guidelines for academic review.
- **Role**: `researcher`, `clinician` | **Scope**: `evidence:view` | **Plan**: All
- **Acceptance Criteria**:
  1. Search executes against `clinical_literature` with `tenant_id = 'system'`.
  2. Returns chunk title, chapter, page number, relevance score, and text.
  3. Zero patient data accessed or queried.

### US-LIT-02: Evidence Drawer Context Inspection
- **As a** Resident Physician
- **I want to** click a citation footnote and inspect the full source passage
- **So that** I can independently confirm the AI's clinical interpretation.
- **Role**: `clinician` | **Scope**: `evidence:view` | **Plan**: All
- **Acceptance Criteria**:
  1. Displays full text of the medical chunk with highlighted matching excerpt.
  2. Shows publication name, authors, edition, chapter, and page number.
  3. Displays active SNOMED-CT, RxNorm, and LOINC codes associated with the chunk.

---

## 5. Audit, Privacy & Compliance

### US-AUD-01: Immutable Query & Verification Audit Trail
- **As a** Hospital Compliance Officer
- **I want to** review a complete log of all queries, citations, and NLI verification scores
- **So that** our clinical decision support operations satisfy regulatory audit requirements.
- **Role**: `auditor`, `cmo` | **Scope**: `audit:read` | **Plan**: Standard, Enterprise
- **Acceptance Criteria**:
  1. Audit entries record: timestamp, user ID (surrogate), query hash, chunk IDs, NLI scores.
  2. Entries are physically append-only with rolling SHA-256 integrity hash chains.
  3. Searchable by date, user ID, status, and tenant.
  4. Raw PHI is stripped; only tokenized synthetic identifiers are retained.

### US-AUD-02: HIPAA Patient Data Erasure (Right to Erasure)
- **As an** Administrator
- **I want to** permanently purge a patient's data upon formal request
- **So that** the organization complies with HIPAA Safe Harbor and privacy laws.
- **Role**: `admin` | **Scope**: `patient:delete` | **Plan**: All
- **Acceptance Criteria**:
  1. Enqueues `PATIENT_DELETE` async job.
  2. Removes patient record from `patient_timelines` table and vector indices.
  3. Audit log references updated to `[DELETED]` without breaking hash chain integrity.
  4. Job completes with cryptographic verification receipt.

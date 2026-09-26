# Tech Spec: REST & Server-Sent Events (SSE) API Specification

_MedRAG v2.0 Interface Contracts_  
_Standardized against OnRent Enterprise Governance_

---

## 1. Authentication & Tenant Injection

All endpoints require either:
- `Authorization: Bearer <jwt_token>` (for web UI sessions)
- `X-API-Key: <api_key>` (for programmatic / server-to-server integration)

Tenant context is extracted strictly by the `TenantScopeMiddleware` from the validated token claims. **Client-submitted tenant headers are rejected.**

---

## 2. Core Endpoint Specifications

### 2.1 Clinical Query Streaming (`POST /api/v1/clinical/query`)
- **Headers**: `Accept: text/event-stream`
- **Request Body**:
  ```json
  {
    "query_text": "Summarize longitudinal renal decline and evaluate ACE inhibitor tolerance",
    "patient_id": "pat-9912",
    "stream": true
  }
  ```
- **SSE Stream Sequence**:
  1. `event: synthesis_chunk` -> `{"chunk_index": 0, "text": "Patient pat-9912 shows a steady rise in creatinine", "is_final": false}`
  2. `event: citation_verified` -> `{"claim_id": "clm-1", "status": "VERIFIED", "score": 0.94, "source": "Harrison's Nephrology Ch.12"}`
  3. `event: claim_redacted` -> `{"claim_id": "clm-2", "status": "CONTRADICTED", "score": 0.88, "source": "KDIGO Guidelines"}`
  4. `event: synthesis_complete` -> `{"faithfulness": 0.92, "total_claims": 5, "verified": 4, "redacted": 1, "duration_ms": 3120}`

### 2.2 Patient FHIR Ingestion (`POST /api/v1/patients/ingest/fhir`)
- **Request Body**: HL7 FHIR R4 Bundle JSON.
- **Response `202 Accepted`**:
  ```json
  {
    "job_id": "job-88192-fhir",
    "patient_id": "pat-9912",
    "status": "QUEUED"
  }
  ```

### 2.3 Patient Timeline Retrieval (`GET /api/v1/patients/{id}/timeline`)
- **Query Parameters**: `?limit=50&cursor=eyJpZCI6MTB9`
- **Response `200 OK`**: Complete structured `PatientTimeline` aggregate.

### 2.4 Audit Log Query (`GET /api/v1/audit/log`)
- **Scopes Required**: `audit:read`
- **Response `200 OK`**: Paginated list of immutable audit entries with SHA-256 hash proofs.

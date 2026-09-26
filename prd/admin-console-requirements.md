# PRD: Admin Console & Tenant Management Requirements

_MedRAG v2.0 Administrative Subsystem Specification_  
_Standardized against OnRent Enterprise Governance_

---

## 1. Functional Modules

### 1.1 Tenant & Seat Management
- Provision new hospital clinic tenants.
- Configure subscription tier (Community, Clinic Standard, Enterprise).
- Manage seat allocations, invite clinicians, and revoke compromised API keys.
- Real-time display of query consumption against monthly plan quotas.

### 1.2 Background Job Supervision (ARQ Monitor)
- Real-time dashboard of background worker queues (`ingestion`, `indexing`, `verification`, `privacy`).
- Status filtering: `QUEUED`, `PROCESSING`, `COMPLETED`, `FAILED`, `DEAD_LETTER`.
- Administrative manual retry trigger for failed jobs with modified parameters.
- Dead-letter queue inspection with error trace visualization.

### 1.3 Query Pipeline Debugger (Enterprise Tier)
- Pipeline replay tool allowing administrators and clinical directors to trace any executed query.
- Inspection of each execution stage:
  1. Extracted SNOMED-CT / RxNorm ontology codes.
  2. LanceDB hybrid retrieval candidates (dense cosine score + sparse BM25 score).
  3. Re-ranked candidate order (MiniLM logits).
  4. Raw LLM output prior to NLI decomposition.
  5. Sentence-by-sentence NLI entailment and contradiction scores.

### 1.4 System Telemetry & Component Health
- Live connection state and latency sparklines for:
  - LanceDB local disk storage.
  - HuggingFace embedding / NLI pipeline models.
  - LLM synthesis serving endpoint (vLLM / LM Studio).
  - Redis broker & ARQ worker processes.

---

## 2. Security & Operational Boundaries

- **Zero Direct Database Writes**: Admin console interacts exclusively via versioned FastAPI admin endpoints enforcing `tenant:manage` and `system:health` scopes.
- **Audit Logging**: All administrative actions (user invitations, key revocations, job retries) are written to the immutable audit trail.

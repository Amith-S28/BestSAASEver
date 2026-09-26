# Tech Spec: Domain Event Architecture & Envelope Schema

_MedRAG v2.0 Event Sourcing & Domain Facts_  
_Standardized against OnRent Enterprise Governance_

---

## 1. Domain Event Philosophy

Domain Events represent **immutable clinical and system facts** that have occurred in the past. They reflect ubiquitous language events, not low-level technical operations:
- ✅ `clinical_query.completed` (domain event)
- ✅ `claim.contradicted` (domain safety event)
- ❌ `redis.hset_completed` (infrastructure detail)

---

## 2. Canonical JSON Event Envelope

All events emitted to the in-process event bus or audit log adhere to the standard envelope schema:

```json
{
  "event_id": "c71a3962-4f3b-4890-84c1-69449830573e",
  "event_name": "claim.contradicted",
  "version": 1,
  "occurred_at": "2026-09-25T14:30:00.123456Z",
  "producer": "medrag.nli_verifier",
  "tenant": {
    "tenant_id": "tenant-mayo-01",
    "clinic_id": "clinic-cardiology-02"
  },
  "actor": {
    "user_id": "usr-99482",
    "role": "clinician"
  },
  "payload": {
    "claim_id": "clm-4821",
    "query_id": "qry-1029",
    "source_document": "Harrison's Principles of Internal Medicine",
    "chapter": "Chapter 275: Cardiogenic Shock",
    "page": 1942,
    "claim_text": "Initiate high-dose beta-blocker therapy immediately.",
    "contradiction_score": 0.942,
    "entailment_score": 0.012
  }
}
```

---

## 3. Core Event Catalog

| Event Name | Producer | Primary Consumers | Action Triggered |
|---|---|---|---|
| `patient.timeline_created` | FHIR Ingester | Audit Logger, UI Notifications | In-app notification |
| `patient.timeline_merged` | FHIR Ingester | Audit Logger | Timeline delta counter |
| `patient.deleted` | Privacy Service | Vector Store, Audit Logger | Purge patient vectors |
| `claim.contradicted` | NLI Verifier | Redaction Engine, Alert System | Immediate sentence redact & CMO alert |
| `claim.manually_overridden`| CMO Controller | Audit Logger, Metrics | Update status to CMO Verified |
| `tenant.quota_exceeded` | Rate Limiter | Notification Service, API Gateway | Block further queries |

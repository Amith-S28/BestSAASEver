# PRD: Clinical Notification & Operational Alert Templates

_MedRAG v2.0 Notification Architecture_  
_Standardized against OnRent Enterprise Governance_

---

## 1. Notification Event Catalog

### NOTIF-01: Critical Lab Flag Detected
- **Trigger**: Ingestion of `LabObservation` with `flag in (CRITICAL_HIGH, CRITICAL_LOW)`.
- **Recipient**: Clinicians assigned to patient's clinic.
- **Delivery**: In-app toast + Webhook notification.
- **Template**:
  > **[CRITICAL LAB ALERT]** Patient `{{patient_surrogate_id}}` recorded critical observation `{{observation_name}}`: **{{value}} {{unit}}** (Reference: {{ref_low}} - {{ref_high}}) at {{observed_at}}. Clinical review required immediately.

### NOTIF-02: Contradicted Clinical Claim Redacted
- **Trigger**: Domain event `claim.contradicted` (`P(Contradiction) >= 0.60`).
- **Recipient**: Chief Medical Officer (CMO) & Safety Auditor.
- **Delivery**: Admin alert banner + High-priority audit queue.
- **Template**:
  > **[SAFETY REDACTION EVENT]** Clinical synthesis query `{{query_id}}` generated a statement contradicting medical literature. Statement: *"{{claim_text}}"* contradicted by **{{source_document}}**, Chapter {{chapter}}, Page {{page}} (Contradiction Score: {{score}}). Output was automatically redacted.

### NOTIF-03: Ingestion Job Completed / Failed
- **Trigger**: Background job completion or failure (`FHIR_BUNDLE_INGEST`, `PDF_LAB_INGEST`).
- **Recipient**: Uploading user.
- **Delivery**: SSE notification + Notification Drawer.
- **Template (Success)**:
  > **[INGESTION COMPLETE]** `{{filename}}` processed successfully. Added {{encounter_count}} encounters and {{observation_count}} observations to patient `{{patient_surrogate_id}}` in {{duration_ms}}ms.
- **Template (Failure)**:
  > **[INGESTION ERROR]** Failed to parse `{{filename}}`. Reason: {{error_message}}. Error Code: `{{error_code}}`. Inspect job `{{job_id}}` for diagnostic details.

### NOTIF-04: Tenant Quota Approaching Limit
- **Trigger**: Monthly query consumption reaching 80% or 95%.
- **Recipient**: Tenant Administrator.
- **Delivery**: Email + Admin console banner.
- **Template**:
  > **[USAGE WARNING]** Tenant `{{tenant_name}}` has utilized {{used_queries}} of {{quota_queries}} queries ({{percent}}%) for the current billing cycle. Upgrade your plan or optimize query volume to avoid disruption.

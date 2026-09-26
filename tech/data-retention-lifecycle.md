# Tech Spec: Data Retention, Cryptographic Erasure & Audit Lifecycle

_MedRAG v2.0 Compliance & Data Governance_  
_Standardized against OnRent Enterprise Governance_

---

## 1. PHI Retention Policies by Plan Tier

| Tier | Patient Timelines | Clinical Query History | Audit Log Entries |
|---|---|---|---|
| **Community** | 90 days active retention | 30 days | 30 days |
| **Clinic Standard** | Active subscription life | 1 year | 1 year |
| **Enterprise** | Active contract + 7 years | 7 years (HIPAA standard) | 7 years immutable WORM |

---

## 2. Right to Erasure Execution (Cryptographic Purge)

When a patient right-to-erasure request is submitted (`DELETE /api/v1/patients/{id}`):
1. Async job `PATIENT_DELETE` is triggered.
2. The row in `patient_timelines` matching `(tenant_id, patient_id)` is permanently deleted.
3. Any patient-specific embeddings in LanceDB are purged.
4. References in `audit_log` have the `entity_id` scrubbed and replaced with `[PURGED_PATIENT_UUID]`, while preserving the rolling SHA-256 hash chain.
5. Emits domain event `patient.deleted` with cryptographic audit signature.

---

## 3. Nightly Hash Chain Integrity Verification

Audit log immutability is validated nightly by a scheduled job (`scripts/verify_audit_integrity.py`):
1. Reads all audit entries chronologically.
2. Re-computes: `curr_hash = SHA256(prev_hash + log_id + action + occurred_at)`.
3. If computed hash deviates from stored `curr_hash`:
   - System immediately triggers critical alert `security.audit_integrity_violation`.
   - Freezes administrative modification endpoints.

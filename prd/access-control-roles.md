# PRD: Access Control, Roles & Scope Matrix

_MedRAG v2.0 Multi-Tenant Security & RBAC Specification_  
_Standardized against OnRent Enterprise Governance_

---

## 1. System Roles & Clinical Responsibilities

| Role Name | Scope Target | Typical Hospital Title |
|---|---|---|
| **clinician** | Clinical query, patient timeline exploration, evidence viewing | Attending Physician, Resident, Fellow |
| **cmo** | Clinical operations, audit review, manual NLI override | Chief Medical Officer, Department Chair |
| **auditor** | Read-only audit log inspection, compliance export | Privacy Officer, External Quality Inspector |
| **researcher** | Literature query only (zero patient access) | Clinical Trialist, Epidemiologist |
| **admin** | Full tenant lifecycle, user management, quota allocation | Enterprise IT Specialist, PACS Admin |

---

## 2. Granular Scope Matrix

| API Scope | Description | clinician | cmo | auditor | researcher | admin |
|---|---|---|---|---|---|---|
| `patient:read` | View patient timeline, encounters, lab trends | ✅ | ✅ | ❌ | ❌ | ✅ |
| `patient:write` | Ingest FHIR bundles, upload lab PDFs | ✅ | ✅ | ❌ | ❌ | ✅ |
| `patient:delete` | Purge patient timeline (Right to Erasure) | ❌ | ✅ | ❌ | ❌ | ✅ |
| `query:execute` | Run clinical synthesis queries | ✅ | ✅ | ❌ | ✅ | ✅ |
| `query:view_history`| Inspect previous queries in tenant | ✅ | ✅ | ✅ | ✅ | ✅ |
| `evidence:view` | View medical chunks and citations | ✅ | ✅ | ✅ | ✅ | ✅ |
| `audit:read` | Read immutable query and claim audit logs | ❌ | ✅ | ✅ | ❌ | ✅ |
| `audit:export` | Export compliance audit archives | ❌ | ✅ | ✅ | ❌ | ✅ |
| `tenant:manage` | Provision tenants, update seat quotas | ❌ | ❌ | ❌ | ❌ | ✅ |
| `user:manage` | Invite clinicians, rotate API keys | ❌ | ❌ | ❌ | ❌ | ✅ |
| `corpus:manage` | Upload hospital guidelines, trigger re-index | ❌ | ❌ | ❌ | ❌ | ✅ |
| `system:health` | Access subsystem telemetry and status | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## 3. Scope Resolution Algorithm

1. Incoming requests pass through `AuthMiddleware`.
2. Token or API Key is decoded; claims extracted: `{tenant_id, clinic_id, user_id, role, scopes}`.
3. If requested endpoint requires scope `S` and `S not in user.scopes`, immediate `403 Forbidden` is returned with `error_code: "INSUFFICIENT_SCOPE"`.
4. Downstream handlers receive validated, scoped `AuthenticatedUser` object.

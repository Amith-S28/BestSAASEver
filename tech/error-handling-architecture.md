# Tech Spec: Typed Exception Hierarchy & Error Handling

_MedRAG v2.0 Clinical Exception Architecture_  
_Standardized against OnRent Enterprise Governance_

---

## 1. Architectural Rules for Error Handling

1. **NO GENERIC EXCEPTIONS**: `raise Exception()`, `raise ValueError()`, or raw FastAPI `HTTPException` are banned across all business and application layers.
2. **CENTRAL HIERARCHY**: All domain and operational exceptions inherit from `ClinicalException`.
3. **MANDATORY ATTRIBUTES**: Every exception specifies an `error_code`, human-readable `message`, HTTP `status_code`, and contextual `details` dictionary.
4. **NO PHI IN ERROR MESSAGES**: Error messages must never include raw patient names, unmasked dates of birth, or sensitive clinical text.

---

## 2. Exception Hierarchy Class Tree

```text
ClinicalException (Base)
├── PatientNotFoundException (404)
├── ChunkNotFoundException (404)
├── IngestionCorruptedException (400)
├── InvalidFHIRResourceException (400)
├── TenantIsolationViolationException (403)
├── InsufficientScopeException (403)
├── UnverifiedClinicalClaimException (422)
├── QuotaExceededException (429)
└── ModelUnavailableException (503)
```

---

## 3. Global Exception Handler & Structured Response Format

All unhandled exceptions are caught by a global FastAPI exception handler and formatted into a uniform JSON response contract:

```json
{
  "error_code": "TENANT_ISOLATION_VIOLATION",
  "message": "Cross-tenant data access blocked by security boundary.",
  "details": {
    "attempted_tenant": "tenant-002",
    "authenticated_tenant": "tenant-001"
  },
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736"
}
```

# Cursor Rule: Mandatory Multi-Tenant Storage Scoping

## Rule Invariant
1. Every query executed against LanceDB or any storage repository MUST enforce a compound predicate containing `tenant_id`.
2. Repositories must raise `TenantIsolationViolationException` if `tenant_id` is missing or empty.
3. Client-submitted tenant headers or query parameters must never be trusted without cryptographic validation.

### ✅ DO
```python
async def get_patient_timeline(self, tenant_id: str, patient_id: PatientId) -> Optional[PatientTimeline]:
    if not tenant_id:
        raise TenantIsolationViolationException("Empty tenant context")
    results = self.table.search().where(f"tenant_id = '{tenant_id}' AND patient_id = '{patient_id.value}'").to_arrow()
```

### ❌ DON'T
```python
# FORBIDDEN: Unscoped query
results = self.table.search().where(f"patient_id = '{patient_id.value}'").to_arrow()
```

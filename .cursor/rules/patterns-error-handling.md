# Cursor Rule: Typed Exception Hierarchy & Error Codes

## Rule Invariant
1. Banned: `raise Exception()`, `raise ValueError()`, `except Exception: pass`.
2. All errors must inherit from `ClinicalException` and specify `error_code`, `status_code`, and `details`.
3. Never expose unformatted stack traces or raw PHI in API error payloads.

### ✅ DO
```python
from medrag.domain.exceptions import PatientNotFoundException

if not patient:
    raise PatientNotFoundException(patient_id=pid)
```

### ❌ DON'T
```python
if not patient:
    raise ValueError(f"Patient {pid} not found in database")
```

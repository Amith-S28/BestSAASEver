# Cursor Rule: Hexagonal Architecture Boundary Enforcement

## Rule Invariant
The domain layer in `src/medrag/domain/` MUST NEVER import any external library or framework. Only Python standard library modules (`dataclasses`, `datetime`, `enum`, `typing`, `uuid`, `abc`) and sibling domain modules are permitted.

### ✅ DO
```python
# Pure domain dataclass in src/medrag/domain/patient.py
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class PatientId:
    value: str
```

### ❌ DON'T
```python
# FORBIDDEN: External import in domain
from pydantic import BaseModel
import lancedb
from fastapi import HTTPException
```

## Enforcement
This rule is strictly checked by `scripts/lint_domain_imports.py`. Any violating commit will be blocked by git pre-commit hooks and CI.

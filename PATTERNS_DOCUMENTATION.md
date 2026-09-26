# MedRAG v2.0: Canonical Architectural Patterns & Anti-Patterns

_Reference Guide for Developers & Code Generation Agents_  
_Standardized against OnRent Enterprise Engineering Governance_

---

## 1. Domain Layer Isolation (Hexagonal Architecture)

### Core Rule
The domain layer (`src/medrag/domain/`) represents pure business truth and clinical invariants. It MUST NEVER import external libraries (e.g. `fastapi`, `lancedb`, `pydantic`, `torch`, `sqlalchemy`, `requests`, `httpx`). It permits ONLY Python stdlib modules (`dataclasses`, `datetime`, `enum`, `typing`, `uuid`, `abc`).

### ✅ DO
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from enum import Enum
import uuid

@dataclass(frozen=True)
class PatientId:
    value: str
    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("PatientId cannot be empty")
```

### ❌ DON'T
```python
# FORBIDDEN: Framework leakage in domain entity
from pydantic import BaseModel
from lancedb import Table
from fastapi import HTTPException

class PatientModel(BaseModel):
    patient_id: str
```

---

## 2. Port Protocols & Dependency Inversion

### Core Rule
External capabilities (database storage, embedding models, LLM text generation, re-ranking) must be defined as structural Protocols in `src/medrag/ports/`. High-level application logic calls ports, never concrete adapters.

### ✅ DO
```python
# src/medrag/ports/storage.py
from typing import Protocol, List, Optional
from medrag.domain.literature import RetrievedEvidence

class IVectorStore(Protocol):
    async def query_hybrid(
        self, tenant_id: str, query_vector: List[float], query_text: str,
        snomed_filters: Optional[List[str]] = None, top_k: int = 25
    ) -> List[RetrievedEvidence]: ...
```

### ❌ DON'T
```python
# FORBIDDEN: Direct adapter instantiation in domain or application service
import lancedb
db = lancedb.connect("./data/lancedb")
```

---

## 3. Mandatory Multi-Tenant Scoping

### Core Rule
Every database query, search filter, cache key, and background job must explicitly specify `tenant_id`. Any query lacking a tenant predicate must be rejected at the repository layer.

### ✅ DO
```python
table.search(vector).where(f"tenant_id = '{tenant_id}' AND clinic_id = '{clinic_id}'")
```

### ❌ DON'T
```python
# FORBIDDEN: Unscoped global query leaking cross-tenant PHI
table.search(vector).limit(10)
```

---

## 4. Typed Clinical Exception Hierarchy

### Core Rule
Never raise generic exceptions (`raise Exception()`, `raise ValueError()`) or raw FastAPI `HTTPException`. All domain and application errors inherit from `ClinicalException`.

### ✅ DO
```python
from medrag.domain.exceptions import PatientNotFoundException

if not patient:
    raise PatientNotFoundException(patient_id=pid)
```

### ❌ DON'T
```python
if not patient:
    raise HTTPException(status_code=404, detail="Patient not found")
```

---

## 5. Deterministic Sentence-Level Verification

### Core Rule
All LLM output must be deconstructed into discrete claims, cross-checked via NLI against retrieved context chunks, and assigned entailment scores. Contradictions (`score >= 0.60`) must be automatically redacted.

### ✅ DO
```python
if footnote.contradiction_score >= 0.60:
    redacted_claim_count += 1
    safe_text = f"[Safety Filter: Recommendation redacted due to contradiction with {footnote.source_document}]"
```

### ❌ DON'T
```python
# FORBIDDEN: Direct streaming of unverified synthesis without claim audit
return StreamingResponse(llm.generate(prompt))
```

---

## 6. Four-Eyes CMO Human-In-The-Loop Override

### Core Rule
Contradicted clinical statements can never be silently overridden by arbitrary actors. Overrides require Chief Medical Officer (`cmo`) or Administrator credentials, a mandatory clinical justification taxonomy (`clinical_judgment`, `institutional_protocol`, `recent_literature`), and an immutable regulatory audit trail entry.

### ✅ DO
```python
# Application service enforcing Four-Eyes principle
workflow = CMOOverrideWorkflow()
overridden_report = workflow.apply_override(
    report=domain_report,
    claim_id=claim_id,
    user_id=cmo_user_id,
    reason=justification_category,
)
audit_log.record_event("claim.overridden", tenant_id=tenant_id, user_id=cmo_user_id, ...)
```

---

## 7. SSE Streaming with Structured Telemetry Protocol

### Core Rule
Real-time streaming responses must emit standard SSE events: `synthesis_chunk` for progressive text tokens, `citation_verified` for entailed claims, `claim_redacted` for filtered contradictions, and `synthesis_complete` containing final latency, verification ratio, and overall faithfulness scores.

---

## 8. Zero-Loss Longitudinal FHIR Timeline Ingestion

### Core Rule
Ingestion of HL7 FHIR R4 bundles or diagnostic PDFs must preserve atomic encounter timelines, maintain reference range high/low values, flag abnormal observations, map SNOMED/LOINC/RxNorm codes, and apply Last-Write-Wins merging without cross-encounter data corruption.


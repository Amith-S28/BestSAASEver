# Tech Spec: Hexagonal Architecture, Port Protocols & Boundary Enforcement

_MedRAG v2.0 Ports & Adapters Architecture_  
_Standardized against OnRent Enterprise Governance_

---

## 1. Boundary Rules & Dependency Direction

The core tenet of MedRAG v2.0 is **Hexagonal Domain Isolation (Ports & Adapters)**. 

### The Dependency Rule
- Dependencies point **INWARD ONLY**.
- `interfaces` → `application` → `ports` ← `domain`
- `infrastructure` → `ports` & `domain`
- **`domain` imports NOTHING outside stdlib.**

```text
       ┌────────────────────────┐
       │   FastAPI / CLI / SSE  │ (Interfaces)
       └───────────┬────────────┘
                   ▼
       ┌────────────────────────┐
       │  Application Services  │ (Application)
       └─────┬────────────┬─────┘
             │            │
             ▼            ▼
       ┌───────────┐ ┌──────────┐
       │  Domain   │ │  Ports   │ (Core Hexagon)
       │ (Pure Py) │ │(Protocol)│
       └───────────┘ └────▲─────┘
                          │ implements
       ┌──────────────────┴─────┐
       │ LanceDB / DeBERTa/ ARQ │ (Infrastructure)
       └────────────────────────┘
```

---

## 2. Hard Machine-Enforced Boundary Linter

To guarantee the hexagonal boundary never degrades under deadline pressure, an AST-level import linter is enforced via pre-commit and CI (`scripts/lint_domain_imports.py`).

### Verification Algorithm
1. Recursively discover all `.py` files in `src/medrag/domain/`.
2. Parse each file into an Abstract Syntax Tree (`ast.parse`).
3. Inspect all `Import` and `ImportFrom` nodes.
4. Permitted modules:
   - Python stdlib: `dataclasses`, `datetime`, `enum`, `typing`, `uuid`, `abc`, `math`, `re`
   - Internal domain references: `medrag.domain.*`
5. **ANY external package import (`fastapi`, `pydantic`, `lancedb`, `torch`, `httpx`) terminates the script with exit code 1 and blocks the git commit.**

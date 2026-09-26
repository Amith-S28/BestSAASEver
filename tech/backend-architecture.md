# Tech Spec: Modular Monolith Backend Architecture & Async Lifecycle

_MedRAG v2.0 Technical Specification_  
_Standardized against OnRent Enterprise Governance_

---

## 1. System Topology & Architectural Style

MedRAG v2.0 is structured as an **Async Modular Monolith** implemented with **FastAPI**, **Python 3.11+**, and **Hexagonal Domain Boundaries**. 

### 1.1 Structural Package Topology
```text
src/medrag/
├── domain/                  # Invariant clinical models & typed exceptions (zero external deps)
├── ports/                   # Abstract typing.Protocol interfaces
├── application/             # Application orchestration use cases & query handlers
│   ├── queries/             # Clinical query, literature search, audit log retrieval
│   ├── commands/            # Patient ingestion, manual claim override, patient deletion
│   └── services/            # Token budgeter, prompt composer, claim tokenizer
├── infrastructure/          # Concrete adapters implementing ports
│   ├── storage/             # LanceDB Arrow adapter, Tantivy BM25 adapter
│   ├── models/              # SentenceTransformers, DeBERTa NLI, vLLM / OpenAI client
│   ├── jobs/                # ARQ / Redis job queue client & worker daemon
│   └── security/            # Argon2id password hashing, JWT encoder/decoder
└── interfaces/              # External entry points
    ├── api/                 # FastAPI routes, middlewares, dependency injection
    └── cli/                 # Typer command-line operational tools
```

---

## 2. Dependency Injection Container

Dependencies are instantiated once during application startup and injected into route handlers using FastAPI's dependency injection pattern:

```python
# src/medrag/interfaces/api/dependencies.py
from fastapi import Depends
from medrag.ports.storage import IVectorStore, ITimelineRepository
from medrag.ports.synthesis import ILanguageModel
from medrag.ports.verification import INLIVerifier
from medrag.infrastructure.container import AppContainer

def get_container() -> AppContainer:
    return AppContainer.get_instance()

def get_vector_store(container: AppContainer = Depends(get_container)) -> IVectorStore:
    return container.vector_store

def get_timeline_repo(container: AppContainer = Depends(get_container)) -> ITimelineRepository:
    return container.timeline_repo

def get_llm(container: AppContainer = Depends(get_container)) -> ILanguageModel:
    return container.llm

def get_nli_verifier(container: AppContainer = Depends(get_container)) -> INLIVerifier:
    return container.nli_verifier
```

---

## 3. Application Lifecycle Management (Lifespan Context)

FastAPI async lifespan manages resource initialization and graceful shutdown:
1. **Startup**:
   - Establish LanceDB connection and ensure Arrow table schemas.
   - Initialize HuggingFace ONNX runtime sessions for embeddings and DeBERTa.
   - Verify connectivity to vLLM endpoint and Redis broker.
2. **Shutdown**:
   - Flush pending audit log batches to disk.
   - Close active Redis connection pools.
   - Release GPU/DirectML context handles cleanly.

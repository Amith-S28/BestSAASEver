# Tech Spec: DevOps, Multi-Stage Docker & Air-Gapped Packaging

_MedRAG v2.0 Infrastructure & Delivery Specification_  
_Standardized against OnRent Enterprise Governance_

---

## 1. Multi-Stage Docker Architecture

```dockerfile
# Stage 1: Build & wheels
FROM python:3.11-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential git
COPY pyproject.toml README.md ./
RUN pip install --upgrade pip && pip wheel --no-cache-dir --wheel-dir /wheels .

# Stage 2: Production API Runtime
FROM python:3.11-slim AS api
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl
COPY src/ /app/src/
EXPOSE 8000
CMD ["uvicorn", "medrag.interfaces.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Stage 3: Background Worker Daemon
FROM api AS worker
CMD ["python", "-m", "medrag.infrastructure.jobs.worker"]
```

---

## 2. Air-Gapped Model Bundle Specification (Amendment 11)

For strictly offline or air-gapped hospital networks, models are distributed as a single versioned archive:

```text
medrag-models-v1.0.tar.gz
├── embeddings/bge-large-en-v1.5/          (~1.3 GB)
├── rerankers/ms-marco-MiniLM-L-6-v2/     (~50 MB)
├── nli/deberta-v3-large-mnli/             (~1.3 GB)
├── synthesis/Qwen2.5-32B-Instruct-GGUF/  (~18 GB, Q4_K_M)
├── corpus/tier1-open-access.parquet       (~2.0 GB)
└── manifest.json                          (Cryptographic SHA-256 digests)
```

The system verifies all digests on startup before opening API ports.

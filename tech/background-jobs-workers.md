# Tech Spec: Background Workers, Job Queues & Distributed Locks

_MedRAG v2.0 Asynchronous Processing Subsystem_  
_Standardized against OnRent Enterprise Governance_

---

## 1. Worker Topology & ARQ / Redis Broker

Background processing runs in a standalone process isolated from the FastAPI HTTP web server, utilizing **ARQ** backed by **Redis**.

```text
┌──────────────────────┐    Enqueues Job     ┌──────────────────────┐
│  FastAPI Web Server  │ ──────────────────► │  Redis / ARQ Broker  │
│  (REST / SSE API)    │ ◄────────────────── │                      │
└──────────────────────┘   Status & Progress └──────────┬───────────┘
                                                        │
                                                        ▼
                                             ┌──────────────────────┐
                                             │ Async Worker Daemon  │
                                             │ (Dedicated Process)  │
                                             └──────────────────────┘
```

---

## 2. Job Catalog & Retry Policies

| Job Type | Queue | Idempotency Key | Max Retries | Backoff Strategy | Description |
|---|---|---|---|---|---|
| `FHIR_BUNDLE_INGEST` | `ingestion` | `tenant:{tid}:fhir:{sha256}` | 3 | Exponential + Jitter | Parse FHIR R4 JSON → PatientTimeline |
| `PDF_LAB_INGEST` | `ingestion` | `tenant:{tid}:pdf:{sha256}` | 3 | Exponential + Jitter | Layout-aware table extraction |
| `CORPUS_REINDEX` | `indexing` | `tenant:{tid}:reindex:{doc_id}` | 2 | Linear (30s) | Re-embed and write textbook chunks |
| `BATCH_EMBED` | `indexing` | `tenant:{tid}:embed:{batch_hash}` | 2 | Dynamic batch halving on OOM | Batch vectorization |
| `NLI_BATCH_VERIFY` | `verification` | `query:{qid}:nli` | 1 | None | Batch DeBERTa evaluation |
| `PATIENT_DELETE` | `privacy` | `tenant:{tid}:delete:{pid}` | 3 | Exponential | HIPAA Safe Harbor purge |
| `TENANT_DATA_EXPORT`| `privacy` | `tenant:{tid}:export:{ts}` | 2 | Linear | Full tenant audit export ZIP |
| `AUDIT_LOG_ARCHIVE` | `maintenance` | `archive:{date}` | 1 | None | WORM storage batch push |

---

## 3. Distributed Lock Protocol

To prevent write collisions during patient updates, workers acquire distributed locks using Redis `SETNX`:
- Key: `lock:tenant:{tenant_id}:patient:{patient_id}`
- TTL: 30 seconds (auto-released on worker death)
- Retry: 5 attempts with 500ms delay.

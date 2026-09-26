# Cursor Rule: Background Job Idempotency & Retries

## Rule Invariant
1. Every background job must declare a deterministic `idempotency_key` based on payload hashes.
2. Concurrent patient ingestion jobs must acquire a Redis distributed lock: `lock:tenant:{tid}:patient:{pid}`.
3. Batch jobs must implement dynamic batch size halving upon catching `MemoryError` to prevent process termination.

### ✅ DO
```python
idempotency_key = f"tenant:{tenant_id}:fhir:{hashlib.sha256(bundle_bytes).hexdigest()}"
await job_queue.enqueue("FHIR_BUNDLE_INGEST", payload, tenant_id=tenant_id, idempotency_key=idempotency_key)
```

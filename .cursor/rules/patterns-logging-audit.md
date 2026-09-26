# Cursor Rule: Structured JSON Logging & PHI Masking

## Rule Invariant
1. All application logs must be output as structured JSON via `structlog`.
2. Raw PHI (patient names, unmasked dates of birth, MRNs) must NEVER be written to stdout or logs. Use HMAC-SHA256 surrogate keys.
3. Every log entry must include `tenant_id` and OpenTelemetry `trace_id`.

### ✅ DO
```python
logger.info(
    "clinical_query_executed",
    tenant_id=tenant_id,
    user_id=user_id,
    query_id=query_id,
    claim_count=len(report.verified_footnotes),
    faithfulness=report.overall_faithfulness
)
```

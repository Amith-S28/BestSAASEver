# Tech Spec: Operational Runbooks & Disaster Recovery

_MedRAG v2.0 Site Reliability & Maintenance Protocols_  
_Standardized against OnRent Enterprise Governance_

---

## 1. Runbook 01: LanceDB Index Corruption Recovery
- **Symptoms**: Vector search queries return internal Arrow errors or fail with index read exceptions.
- **Remediation Procedure**:
  1. Freeze ingestion worker: `systemctl stop medrag-worker`.
  2. Run integrity check script: `python scripts/check_lancedb_health.py`.
  3. Rebuild IVF-PQ vector index: `python scripts/rebuild_indices.py --table clinical_literature`.
  4. If corruption persists, restore Parquet backup from immutable archive.
  5. Restart worker and verify health telemetry.

---

## 2. Runbook 02: Local Model Offline or Out-Of-Memory (OOM)
- **Symptoms**: Query endpoint returns `503 Service Unavailable` with `MODEL_UNAVAILABLE`.
- **Remediation Procedure**:
  1. Inspect GPU memory utilization via `nvidia-smi`.
  2. If VRAM exhausted, restart local vLLM / LM Studio process.
  3. System will automatically engage fallback chain: Local vLLM → Secondary LM Studio → CPU ONNX fallback.
  4. Reduce worker batch size parameter: `BATCH_SIZE=16`.

---

## 3. Runbook 03: Cross-Tenant Security Incident Response
- **Symptoms**: Alert `CrossTenantAccessAttempt` fires or `tenant_boundary_violation_total` increments.
- **Remediation Procedure**:
  1. Automated isolation immediately suspends the offending API key.
  2. Query audit log: `GET /api/v1/audit/log?action=security.tenant_violation`.
  3. Review trace ID in OpenTelemetry to determine if violation originated from misconfigured token or deliberate exploit.
  4. Notify Hospital Privacy Officer within 1 hour as required by HIPAA breach protocol.

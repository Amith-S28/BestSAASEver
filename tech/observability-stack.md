# Tech Spec: Observability, Metrics & Telemetry Stack

_MedRAG v2.0 Monitoring & Telemetry Specification_  
_Standardized against OnRent Enterprise Governance_

---

## 1. Observability Triad Architecture

1. **Distributed Tracing**: OpenTelemetry auto-instrumentation on FastAPI, LanceDB operations, and async background workers.
2. **Prometheus Metrics**: High-precision counters and latency histograms exported on `/metrics` endpoint.
3. **Structured JSON Logging**: Structlog library generating machine-parsable logs with automatic PHI masking and trace correlation (`trace_id`).

---

## 2. Core Prometheus Metrics Catalog

| Metric Identifier | Metric Type | Labels | Description |
|---|---|---|---|
| `medrag_query_duration_seconds` | Histogram | `tenant_id`, `model` | End-to-end query latency (p50, p95, p99) |
| `medrag_nli_score_distribution` | Histogram | `status` | Entailment / Contradiction score distribution |
| `medrag_contradictions_total` | Counter | `tenant_id` | Total claims automatically redacted |
| `medrag_lancedb_search_ms` | Histogram | `table`, `type` | Vector search vs Tantivy BM25 search latency |
| `medrag_tenant_queries_total` | Counter | `tenant_id`, `plan` | Monthly consumption tracking |
| `medrag_tenant_violations_total` | Counter | `tenant_id` | Blocked cross-tenant data access attempts |
| `medrag_ingestion_seconds` | Histogram | `job_type`, `status` | Time to process FHIR / PDF files |

---

## 3. High-Severity Alert Rules

```yaml
groups:
  - name: medrag_clinical_alerts
    rules:
      - alert: HighContradictionRate
        expr: rate(medrag_contradictions_total[5m]) > 0.10
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Abnormal surge in contradicted recommendations (>10% of claims). Synthesis halted."

      - alert: CrossTenantAccessAttempt
        expr: increase(medrag_tenant_violations_total[1m]) > 0
        labels:
          severity: critical
        annotations:
          summary: "Cross-tenant PHI access attempt detected. API key isolated."
```

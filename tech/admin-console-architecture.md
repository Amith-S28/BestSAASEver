# Tech Spec: Admin Console Architecture & Telemetry Dashboard

_MedRAG v2.0 Administrative UI Architecture_  
_Standardized against OnRent Enterprise Governance_

---

## 1. Architectural Philosophy

The Admin Console is a protected, read-heavy, write-light application module accessible only to users with `admin` or `cmo` roles:
- **No Separate Backend**: Interacts with the platform solely via standardized, RBAC-protected FastAPI admin endpoints (`/api/v1/admin/*`).
- **Telemetry Polling**: Health and job metrics poll every 15-30 seconds via SWR / React Query.
- **Zero Raw PHI**: The console never renders raw clinical data; all identifiers are synthetic surrogate keys.

---

## 2. Key Administrative Views

1. **Tenant Dashboard**: Real-time visualization of query consumption, monthly quota ceilings, storage utilization (MB), and seat allocations.
2. **Job Queue Monitor**: Interactive table of ARQ background jobs with manual retry triggers for failed jobs and dead-letter queue inspections.
3. **Audit Explorer**: Paginated, filterable interface querying the immutable audit log table, with one-click signed compliance export.
4. **Query Pipeline Replay**: Visual breakdown of clinical query execution: pre-filters, vector search scores, re-ranked candidate order, raw LLM tokens, and DeBERTa claim scores.

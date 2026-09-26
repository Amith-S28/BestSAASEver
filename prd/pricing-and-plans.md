# PRD: SaaS Subscription Tiers, Plan Quotas & Rate Limits

_MedRAG v2.0 Commercial & Quota Governance_  
_Standardized against OnRent Enterprise Governance_

---

## 1. Commercial Plan Tiers

| Dimension | Community Tier | Clinic Standard | Enterprise Hospital |
|---|---|---|---|
| **Target Customer** | Independent clinics, researchers | Community hospitals, group practices | Health systems, academic centers |
| **Clinician Seats** | 1 Seat | Up to 15 Seats | Unlimited |
| **Monthly Queries** | 250 Queries | 5,000 Queries | 100,000+ Queries |
| **Patient Capacity** | 50 Timelines | 2,500 Timelines | Unlimited |
| **Rate Limit** | 10 req/min, 2 concurrent | 60 req/min, 10 concurrent | 300 req/min, 50 concurrent |
| **NLI Verification** | Standard DeBERTa | Standard DeBERTa + CMO Override | Custom Thresholds + Multi-step |
| **Corpus Support** | Shared Open-Access (Tier 1) | Tier 1 + Custom Guidelines | Tier 1, 2 + Institutional Protocols |
| **Audit Retention** | 30 Days | 1 Year | 7 Years (HIPAA Compliant) |
| **Deployment Mode** | Local / Shared SaaS | Dedicated Instance | On-Premises / Air-Gapped |

---

## 2. Token-Bucket Rate Limiting Architecture

1. **Bucket Tracking**: Redis token-bucket per `tenant_id`.
2. **Quota Counting**: Atomic Redis `INCR` on query execution.
3. **Threshold Alerts**:
   - At 80% quota: Warning event `tenant.quota_warning` emitted to admin console.
   - At 95% quota: High-severity alert to tenant administrator.
   - At 100% quota: New queries rejected with `429 Too Many Requests` and `QuotaExceededException`.
4. **No Silent Degraded Failure**: System never returns pseudo-data or silent truncation when quotas are exceeded.

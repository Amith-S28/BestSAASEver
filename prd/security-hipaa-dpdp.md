# PRD: Healthcare Security, HIPAA Safe Harbor & DPDP Compliance

_MedRAG v2.0 Privacy & Regulatory Governance Specification_  
_Standardized against OnRent Enterprise Governance_

---

## 1. HIPAA Safe Harbor De-Identification (45 CFR § 164.514(b)(2))

MedRAG v2.0 implements automated redaction and tokenization for all 18 HIPAA Safe Harbor identifiers at the ingestion boundary:

1. **Names**: Scrubbed and replaced with synthetic surrogates (`[PATIENT-SURROGATE-ID]`).
2. **Geographic Subdivisions**: All identifiers smaller than state stripped.
3. **Dates**: Except year; transformed according to `date_generalization_policy`:
   - `exact_year`: Default for standard prevalence conditions.
   - `5_year_band`: Required for rare diseases (<1:10,000 prevalence) to mitigate re-identification risks (Amendment 9).
   - `full_suppression`: All dates replaced with sequential encounter ordinals ("Encounter 1", "Encounter 2").
4. **Phone Numbers & Faxes**: Scrubbed via regex and NER.
5. **Email Addresses**: Scrubbed.
6. **Social Security Numbers**: Scrubbed.
7. **Medical Record Numbers (MRN)**: Tokenized via HMAC-SHA256 with secure salt.
8. **Health Plan Beneficiary Numbers**: Scrubbed.
9. **Account Numbers**: Scrubbed.
10. **Certificate / License Numbers**: Scrubbed.
11. **Vehicle Identifiers**: Scrubbed.
12. **Device Identifiers & Serial Numbers**: Scrubbed.
13. **Web URLs**: Scrubbed.
14. **IP Addresses**: Scrubbed.
15. **Biometric Identifiers**: Scrubbed.
16. **Full-Face Photographs**: Excluded from ingestion.
17. **Any Other Unique Identifying Characteristic**: Redacted.

---

## 2. Multi-Tenant Cryptographic Boundaries

| Domain | Protection Standard | Operational Implementation |
|---|---|---|
| **Data-at-Rest** | AES-256 | BitLocker/LUKS encrypted volumes for LanceDB Arrow files |
| **Data-in-Transit** | TLS 1.3 | Enforced on all external HTTP and SSE streaming interfaces |
| **API Keys** | Argon2id | Keys hashed with unique salt; raw secret never persisted |
| **Audit Logs** | Append-Only WORM | Physical LanceDB append; DB role REVOKE on UPDATE/DELETE |
| **Integrity Checks**| SHA-256 Hash Chain | Nightly verification calculating rolling Merkle chain |

---

## 3. Security Breach & Anomaly Incident Response

1. **Detection**: `tenant_boundary_violation_total` metric increments if cross-tenant data access is attempted.
2. **Automatic Containment**: Offending API key immediately suspended; session invalidated.
3. **Notification**: Emits high-priority event `security.tenant_violation` to admin console and on-call pager.
4. **Forensics**: Comprehensive audit export generated within 1 hour for compliance review.

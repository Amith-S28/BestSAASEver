# PRD: V2 Scope & Institutional Integration Architecture

_MedRAG v2.0 Enterprise Vision Specification_  
_Standardized against OnRent Enterprise Governance_

---

## 1. Enterprise Scope Dimensions

MedRAG v2.0 represents the institutional-scale deployment tier, focusing on deep bi-directional EHR interoperability, real-time clinical consult automation, and hospital-wide guideline governance.

### 1.1 Bi-Directional SMART on FHIR Interoperability
- **FHIR R4 Writeback Protocol**:
  - Integration with hospital EHRs via SMART on FHIR OAuth 2.0.
  - Generating standard `DocumentReference` and `ClinicalImpression` resources.
  - Mandatory 2-factor physician sign-off before committing summaries into patient chart.

### 1.2 Enterprise Guideline & Formulary Partitioning
- **Institutional Custom Guidelines (Tier 3 Corpus)**:
  - Hospital pharmacy and therapeutics (P&T) committee guideline management.
  - Overriding general textbook guidance with hospital-specific antimicrobial stewardship policies.
  - Tenant-level cryptographic isolation ensuring hospital guidelines are never accessible to competing institutions.

### 1.3 Federated Multi-Hospital Deployment
- **Edge Inference Nodes**:
  - Deploying isolated inference sidecars behind hospital on-premises firewalls.
  - Centralized policy, license, and model weight synchronization.
  - Zero raw patient telemetry egress to central management plane.

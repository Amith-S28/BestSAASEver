# PRD: Overview, Clinical Personas & System Mental Model

_MedRAG v2.0 Institutional Product Specification_  
_Standardized against OnRent Enterprise Governance_

---

## 1. System Vision & Objective

MedRAG v2.0 is an institutional-grade, multi-tenant Clinical AI Intelligence SaaS Platform designed for healthcare systems, academic medical centers, and clinical consult services. It provides attending physicians, residents, and clinical researchers with sub-second, longitudinal patient encounter synthesis cross-referenced against authoritative medical textbooks and peer-reviewed clinical guidelines, fortified by deterministic Natural Language Inference (NLI) sentence-level verification.

The platform eliminates diagnostic hallucination by transforming generative AI from an ungrounded generator into an auditable clinical evidence synthesizer. Every assertion made by the model is bound to retrieved evidence chunks, scored for entailment, and visibly verified or redacted before clinician review.

---

## 2. Target Personas & Clinical Workflows

### 2.1 Attending Physician (Dr. Sarah Chen, MD - Internal Medicine)
- **Clinical Environment**: High-volume tertiary care inpatient ward.
- **Pain Point**: Spends 45+ minutes reviewing fragmented, multi-year electronic health records (EHR) across disparate hospital encounters before morning rounds.
- **Mental Model**: Needs an atomic chronological narrative showing condition onset, lab trends, and therapeutic interventions, with immediate links to primary medical literature justifying treatment pathways.
- **Primary Actions**:
  - Longitudinal patient summary generation.
  - Verification badge inspection on therapeutic recommendations.
  - Interactive deep-dive into evidence passages via the Evidence Drawer.

### 2.2 Chief Medical Officer / Medical Director (Dr. Marcus Vance, MD, FACP)
- **Administrative Environment**: Hospital Network Quality & Safety Committee.
- **Pain Point**: Fear of medical malpractice liability arising from unverified generative AI hallucinations and unauthorized cross-department PHI leaks.
- **Mental Model**: Demands deterministic safety gates, automated contradiction blocking, full tamper-proof auditability, and human-in-the-loop override capabilities.
- **Primary Actions**:
  - Review contradiction alert summaries.
  - Authorize CMO overrides on uncertain claims with clinical justification.
  - Audit regulatory compliance logs for HIPAA Safe Harbor adherence.

### 2.3 Clinical Research Coordinator (Elena Rostova, MS, CCRP)
- **Research Environment**: Academic Clinical Trials Unit.
- **Pain Point**: Manually scanning hundreds of multi-page scanned PDF lab reports to extract numerical trends against LOINC reference ranges.
- **Mental Model**: Needs high-throughput, layout-aware PDF parsing that extracts tabular lab observations, maps them to standard ontologies, and detects abnormal flags without losing normal reference intervals.
- **Primary Actions**:
  - Batch PDF upload and status tracking.
  - Literature-only semantic search across canonical textbook chapters.
  - Export of structured clinical timeline data.

### 2.4 Hospital IT / System Administrator (David Kim, CISSP)
- **IT Environment**: Healthcare Enterprise Infrastructure & Security.
- **Pain Point**: Cloud vendor lock-in, data sovereignty compliance, and managing seat quotas across multiple hospital clinics.
- **Mental Model**: Requires local-first or private-cloud containerized deployment, strict RBAC isolation, zero data leakage between clinical tenants, and low idle server compute cost.
- **Primary Actions**:
  - Tenant provisioning and API key lifecycle management.
  - Background worker queue health monitoring.
  - Storage quota tracking and automated rate limiting.

---

## 3. Core Product Principles

1. **Safety First, Fluency Second**: A grammatically awkward response with 100% verified evidence is infinitely superior to a fluent diagnostic hallucination.
2. **Deterministic Provenance**: No clinical assertion without sentence-level footnote linkage to source textbook chapters and page numbers.
3. **Zero Data Leakage**: Clinic A must never see Clinic B's patients, queries, or audit trails. Multi-tenancy is enforced in the kernel storage engine.
4. **Physician in the Loop**: The platform provides clinical decision intelligence, not autonomous diagnostics. Clear disclaimers and human overrides maintain clinician agency.

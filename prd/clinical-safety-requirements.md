# PRD: Clinical Safety Requirements & Risk Governance

_MedRAG v2.0 Safety Architecture & Failure Mode Taxonomy_  
_Standardized against OnRent Enterprise Governance_

---

## 1. Regulatory Context & Advisory Boundary

MedRAG v2.0 is designed as a **Non-Device Clinical Decision Support (CDS) Intelligence Tool** under Section 520(o)(1)(E) of the United States Food, Drug, and Cosmetic Act (FD&C Act) and the 21st Century Cures Act.

### Core Non-Device Criteria Enforced by Architecture
1. **No Autonomous Clinical Action**: The software does not acquire, process, or analyze an image or signal from an in vitro diagnostic device or medical sensor in real time.
2. **Independent Reviewability**: The software displays the medical literature rationale, source textbook passage, chapter, and page number for every claim, enabling the licensed healthcare provider to independently review the basis for the recommendations.
3. **Mandatory Advisory Disclaimer**: Every user interface view, API response, and generated document includes the immutable warning:
   > *"Notice: MedRAG is an assistive clinical reference tool. It does not provide medical diagnoses or replace physician clinical judgment. All therapeutic recommendations must be independently confirmed against primary sources and patient-specific context."*

---

## 2. Failure Mode Taxonomy & Mitigations

| Severity Tier | Failure Mode | Clinical Consequence | Automated System Reaction |
|---|---|---|---|
| **Tier 1 (Catastrophic)** | Direct contradiction of treatment guideline (e.g. recommending beta-blocker in cardiogenic shock) | Acute patient injury or death | Automatic redaction (`P(Contradiction) >= 0.60`), audit event `claim.contradicted`, alert to CMO |
| **Tier 2 (High)** | Omission of critical abnormal lab trend (e.g. missed creatinine doubling over 48h) | Delayed diagnosis of acute kidney injury | Ingestion validation forcing abnormal observations to surface in the summary header |
| **Tier 3 (Medium)** | Citation to outdated edition or conflicting literature | Suboptimal clinical choice | Footnote flagged as `UNCERTAIN` (0.50-0.84 entailment); UI displays amber badge |
| **Tier 4 (Low)** | Grammatical awkwardness or minor formatting misalignment | Minor clinician friction | Logged to prompt optimization metrics; does not block synthesis delivery |

---

## 3. Four-Eyes Principle for High-Risk Overrides

Under no circumstances may an individual clinician override a `CONTRADICTED` claim. 
- Overriding a claim flagged as `CONTRADICTED` (`P(Contradiction) >= 0.60`) requires:
  1. Escalation to the hospital Clinical Governance / Pharmacy & Therapeutics Committee.
  2. Formal creation of an admin review ticket.
  3. Digital signatures from two independent Chief Medical Officers (`four_eyes_override`).
  4. Explicit citation of an approved institutional protocol or recent peer-reviewed trial.

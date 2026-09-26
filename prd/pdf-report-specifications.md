# PRD: Diagnostic Summary PDF Report Specifications

_MedRAG v2.0 Clinical Report Generation Standard_  
_Standardized against OnRent Enterprise Governance_

---

## 1. Document Layout Architecture

The exported Diagnostic Summary PDF is a high-fidelity, printable clinical artifact designed for multidisciplinary case reviews, tumor boards, and transfer of care summaries.

### 1.1 Structural Layout Sections
1. **Header Block**:
   - Hospital / Tenant branding banner.
   - De-identified Patient Surrogate Key (`PAT-XXXXXX`), age, gender.
   - Date of report generation, ordering clinician, report UUID.
   - Prominent Advisory Disclaimer Box: *"Clinical Decision Support Intelligence - For Professional Physician Use Only"*.
2. **Clinical Query & Problem Synthesis**:
   - The clinical question or diagnostic inquiry asked.
   - Chronological summary of disease trajectory, encounter progression, and therapeutic history.
   - Inline superscript citation anchors (`[1]`, `[2]`, `[3]`).
3. **Longitudinal Lab Trends & Critical Alerts**:
   - Tabular presentation of abnormal observations with reference ranges.
   - Color-coded severity flags (Amber for abnormal, Red for critical).
4. **Active Medication Schedule**:
   - Active prescriptions with dosages, administration routes, and start dates.
5. **Literature Citation Appendix (Evidence Ledger)**:
   - Footnote 1: Textbook Title, Edition, Chapter, Page Number, Relevant Quote, NLI Verification Score.
   - Footnote 2: Guideline Title, Sponsoring Organization, Publication Year, Section Number.
   - Verification status badge (`VERIFIED [Score: 0.94]` or `CMO OVERRIDDEN`).

---

## 2. Technical Rendering Standards

- **Engine**: Headless Chromium / Weasyprint via serverless background job.
- **Color Palette**: High-contrast, WCAG 2.1 AA accessible healthcare palette.
- **Page Numbering**: "Page X of Y" dynamic running footer.
- **Tamper Resistance**: Embedded cryptographic SHA-256 report fingerprint in document metadata.

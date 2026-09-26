# Tech Spec: Layout-Aware Diagnostic PDF & Table Parsing

_MedRAG v2.0 Unstructured Document Ingestion Engine_  
_Standardized against OnRent Enterprise Governance_

---

## 1. Tiered PDF Parser Cascade (Amendment 7)

Hospital lab reports exhibit massive formatting divergence. Ingestion implements a tiered fallback cascade:

```text
Uploaded PDF
     │
     ▼
┌─────────────────────────┐
│ Tier 1: pdfplumber      │ ──► High confidence (>=0.70)? ──► Output LabObservations
└───────────┬─────────────┘
            ▼ Low Confidence (<0.70)
┌─────────────────────────┐
│ Tier 2: docTR / OCR     │ ──► Success? ──────────────────► Output with Low-Conf Tag
└───────────┬─────────────┘
            ▼ Fail / Corrupt
┌─────────────────────────┐
│ Tier 3: Manual Queue    │ ──► Tag as PARSE_UNCERTAIN in Admin Console Review
└─────────────────────────┘
```

---

## 2. Table Column Detection & Flag Extraction

### Column Header Normalization
The parser recognizes multi-column layouts and aligns columns against standard clinical tokens:
- **Test / Analyte**: e.g., "Creatinine", "WBC", "Hemoglobin A1c"
- **Result / Value**: Numeric floats or strings (e.g. `1.4`, `>100`)
- **Reference Range**: Low and high bounds parsed via regex `(\d+\.?\d*)\s*-\s*(\d+\.?\d*)`
- **Units**: Normalized to UCUM (e.g., `mg/dL`, `g/L`, `mmol/L`)
- **Flags**: Auto-detected or derived (`H`, `L`, `CRIT`, `*`)

### Normalization to Domain Entities
```python
observation = LabObservation(
    code_snomed="113075003",
    code_loinc="2160-0",
    display_name="Serum Creatinine",
    numeric_value=1.8,
    unit="mg/dL",
    reference_low=0.7,
    reference_high=1.3,
    flag=ObservationFlag.HIGH,
    observed_at=datetime(2025, 3, 14, 9, 30),
    raw_text="Creatinine 1.8 H (0.7 - 1.3 mg/dL)"
)
```

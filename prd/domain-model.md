# PRD: Ubiquitous Language & Clinical Domain Model

_MedRAG v2.0 Domain Entities, Relationships & Invariants_  
_Standardized against OnRent Enterprise Governance_

---

## 1. Ubiquitous Language Dictionary

- **PatientTimeline**: The aggregate root encapsulating the complete chronological clinical history of a single patient within a tenant.
- **ClinicalEncounter**: A discrete medical interaction (ambulatory, emergency, inpatient) during which observations are recorded and medications ordered.
- **LabObservation**: A quantitative or qualitative diagnostic test result mapped to LOINC, containing numeric values, units, reference intervals, and severity flags.
- **MedicationRecord**: A pharmaceutical administration or prescription record mapped to RxNorm, indicating drug name, dose, status, and active duration.
- **MedicalChunk**: A semantically coherent textbook passage (<500 tokens) mapped to SNOMED-CT disorders, LOINC codes, and RxNorm ingredients.
- **ClinicalClaim**: An atomic assertive sentence extracted from the generated clinical synthesis.
- **VerifiedFootnote**: The verification evaluation of a claim against retrieved evidence, carrying entailment and contradiction scores.
- **VerificationStatus**: Four-state enum: `VERIFIED`, `UNCERTAIN`, `CONTRADICTED`, `UNGROUNDED`.

---

## 2. Entity Relationship Diagram (Domain Perspective)

```text
┌────────────────────────────────────────────────────────┐
│                     PatientTimeline                    │
│  - patient_id: PatientId (Value Object)                │
│  - tenant_id: TenantId (Value Object)                  │
│  - clinic_id: ClinicId (Value Object)                  │
│  - demographics: Dict[str, Any]                        │
│  - created_at / updated_at: datetime                   │
└───────────────────────────┬────────────────────────────┘
                            │ 1..* contains
                            ▼
┌────────────────────────────────────────────────────────┐
│                    ClinicalEncounter                   │
│  - encounter_id: str                                   │
│  - encounter_type: str (ambulatory|emergency|inpatient)│
│  - start_time / end_time: datetime                     │
│  - chief_complaint: str                                │
└─────────────┬───────────────────────────┬──────────────┘
              │ 0..* contains             │ 0..* contains
              ▼                           ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│      LabObservation      │  │     MedicationRecord     │
│  - code_loinc: str       │  │  - code_rxnorm: str      │
│  - numeric_value: float  │  │  - drug_name: str        │
│  - reference_low/high    │  │  - dosage / route: str   │
│  - flag: ObservationFlag │  │  - status: str           │
└──────────────────────────┘  └──────────────────────────┘
```

---

## 3. Core Business Invariants Enforced in Domain

1. **PatientId & TenantId Non-Emptiness**: Identifier value objects raise `ValueError` if initialized with empty or whitespace-only strings.
2. **Observation Severity Classification**: `LabObservation.is_critical()` evaluates strictly to `True` if flag is `CRITICAL_HIGH` or `CRITICAL_LOW`.
3. **Temporal Monotonicity**: Encounter end time cannot precede start time.
4. **Active Medication Filtering**: `PatientTimeline.active_medications()` extracts only medication records with `status == "active"`.
5. **Safe Display Rule**: `VerifiedFootnote.is_safe_to_display()` returns `True` only when status is `VERIFIED` or `UNCERTAIN`. Contradicted or ungrounded claims are barred from normal display.

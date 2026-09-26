# Tech Spec: HL7 FHIR R4 Ingestion & Longitudinal Timeline Assembly

_MedRAG v2.0 Structured Ingestion Engine_  
_Standardized against OnRent Enterprise Governance_

---

## 1. Supported FHIR R4 Resources

The ingestion pipeline maps standard HL7 FHIR R4 JSON resources directly into pure domain entities:

| FHIR R4 Resource | Domain Entity Mapping | Key Extracted Attributes |
|---|---|---|
| `Patient` | `PatientTimeline` Demographics | `gender`, `birthDate` (generalized to year) |
| `Encounter` | `ClinicalEncounter` | `id`, `class.code`, `period.start`, `period.end`, `reasonCode` |
| `Observation` | `LabObservation` | `code.coding` (LOINC), `valueQuantity`, `referenceRange`, `interpretation` |
| `MedicationRequest` | `MedicationRecord` | `medicationCodeableConcept` (RxNorm), `dosageInstruction`, `status` |
| `Condition` | `Condition` | `code.coding` (SNOMED-CT), `clinicalStatus`, `onsetDateTime` |

---

## 2. Ingestion & Merge Workflow

```text
FHIR Bundle JSON
       │
       ▼
 1. SHA-256 Hash Deduplication (Skip if already ingested)
       │
       ▼
 2. Distributed Lock: LOCK tenant:{tid}:patient:{pid} (Redis 30s TTL)
       │
       ▼
 3. Parse & Validate Structure (Raise IngestionCorruptedException on malformed syntax)
       │
       ▼
 4. Encounter Deduplication & Last-Write-Wins Merge
       │
       ▼
 5. Persist to LanceDB `patient_timelines` Table
       │
       ▼
 6. Release Lock & Emit Domain Event `patient.timeline_created` or `merged`
```

---

## 3. Concurrent Merge Semantics (Amendment 5)

If two bundles for the same patient arrive concurrently:
1. Worker 1 acquires distributed lock on `(tenant_id, patient_id)`.
2. Worker 2 waits and retries.
3. Encounters are merged by `encounter_id`. If duplicate encounter IDs exist, the one with the later `meta.lastUpdated` FHIR timestamp supersedes the older version.
4. New encounters are appended chronologically.
5. Invariant: Longitudinal time series monotonicity is strictly preserved.

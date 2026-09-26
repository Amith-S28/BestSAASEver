# Tech Spec: Testing Strategy & Automated Quality Gates

_MedRAG v2.0 Test Engineering Pyramid_  
_Standardized against OnRent Enterprise Governance_

---

## 1. Test Pyramid Structure

```text
               ▲
              / \     E2E / Security Sweep (1,000 queries)
             /   \    CI Gate: Zero leaks, p95 < 250ms
            /─────\
           /       \   Integration Tests (LanceDB, FHIR, PDF)
          /         \  Coverage Target: 60%+
         /───────────\
        /             \ Unit Tests (Pure Domain Models & Ports)
       /               \Coverage Target: 100% (Domain), 80%+ (Total)
      ───────────────────
```

---

## 2. Unit Testing Mandates (Domain Layer)

1. **Zero External I/O**: Domain tests must execute in memory with zero network, disk, or GPU calls.
2. **Speed Gate**: The entire unit test suite must complete in `< 5 seconds`.
3. **Invariant Verification**:
   - `PatientId` / `TenantId` non-empty string checks.
   - `LabObservation.is_critical()` correctness.
   - `ClinicalEncounter` chronological ordering and critical observation filters.
   - `VerifiedClinicalReport` contradiction detection.

---

## 3. Integration & Contract Testing

- **LanceDB Storage Tests**: Run against temporary disk directories created by pytest `tmp_path` fixtures, deleted during teardown.
- **FHIR Parser Tests**: Evaluated against real Synthea multi-year patient bundles.
- **NLI Engine Tests**: Verified against gold entailment and contradiction sentence pairs.
- **Tenant Boundary Security Sweep**: Automated test asserting that 1,000 queries across synthetic tenants yield zero data cross-contamination.

"""Unit tests for clinical prompt composer service."""

from datetime import datetime, timezone
import pytest

from medrag.application.services.prompt_composer import ClinicalPromptComposer
from medrag.domain.literature import MedicalChunk
from medrag.domain.patient import (
    ClinicId,
    ClinicalEncounter,
    Gender,
    LabObservation,
    MedicationRecord,
    ObservationFlag,
    PatientId,
    PatientTimeline,
    TenantId,
)


def test_prompt_composer_with_patient_and_evidence():
    """Prompt composer incorporates active meds, critical observations, and cited passages."""
    now = datetime.now(timezone.utc)
    obs = LabObservation(
        code_snomed="113075003",
        code_loinc="2160-0",
        display_name="Serum Creatinine",
        numeric_value=2.4,
        unit="mg/dL",
        reference_low=0.7,
        reference_high=1.3,
        flag=ObservationFlag.CRITICAL_HIGH,
        observed_at=now,
        raw_text="Creatinine 2.4 CRIT",
    )
    med = MedicationRecord(
        code_rxnorm="316049",
        drug_name="Lisinopril 10 MG",
        dosage="10 mg oral daily",
        route="oral",
        status="active",
        started_at=now,
    )
    enc = ClinicalEncounter(
        encounter_id="enc-01",
        encounter_type="ambulatory",
        start_time=now,
        chief_complaint="Elevated serum creatinine",
        observations=[obs],
        medications=[med],
    )
    timeline = PatientTimeline(
        patient_id=PatientId("pat-1"),
        tenant_id=TenantId("t-1"),
        clinic_id=ClinicId("c-1"),
        demographics={"age": 68, "gender": Gender.MALE.value},
        encounters=[enc],
        created_at=now,
        updated_at=now,
    )

    chunk = MedicalChunk(
        chunk_id="chk-100",
        document_id="doc-kdigo",
        title="KDIGO AKI Guidelines",
        chapter="Chapter 2: Staging",
        page_number=14,
        text_content="Acute kidney injury stage 2 corresponds to a 2.0 to 2.9 times baseline increase in serum creatinine.",
        specialty="Nephrology",
    )

    composer = ClinicalPromptComposer()
    prompt = composer.compose_prompt(
        query_text="Assess AKI severity and review Lisinopril safety",
        timeline=timeline,
        evidence_chunks=[chunk],
    )

    assert "Lisinopril 10 MG" in prompt
    assert "CRITICAL LAB FLAGS" in prompt
    assert "KDIGO AKI Guidelines" in prompt
    assert "[^1]" in prompt
    assert "Assess AKI severity" in prompt

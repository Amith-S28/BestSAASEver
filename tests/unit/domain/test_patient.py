"""Unit tests for patient domain models and invariants."""

from datetime import datetime
import pytest

from medrag.domain.patient import (
    ClinicId,
    ClinicalEncounter,
    Condition,
    Gender,
    LabObservation,
    MedicationRecord,
    ObservationFlag,
    PatientId,
    PatientTimeline,
    TenantId,
)


def test_patient_id_validation():
    """PatientId enforces non-empty string invariant."""
    pid = PatientId("pat-12345")
    assert pid.value == "pat-12345"

    with pytest.raises(ValueError, match="cannot be empty"):
        PatientId("")

    with pytest.raises(ValueError, match="cannot be empty"):
        PatientId("   ")


def test_tenant_and_clinic_id_validation():
    """TenantId and ClinicId enforce non-empty string invariant."""
    tid = TenantId("tenant-mayo")
    cid = ClinicId("clinic-cardiology")
    assert tid.value == "tenant-mayo"
    assert cid.value == "clinic-cardiology"

    with pytest.raises(ValueError):
        TenantId("")

    with pytest.raises(ValueError):
        ClinicId("   ")


def test_lab_observation_flags():
    """LabObservation correctly identifies abnormal and critical flags."""
    normal_obs = LabObservation(
        code_snomed="113075003",
        code_loinc="2160-0",
        display_name="Creatinine",
        numeric_value=1.0,
        unit="mg/dL",
        reference_low=0.7,
        reference_high=1.3,
        flag=ObservationFlag.NORMAL,
        observed_at=datetime(2025, 1, 1),
        raw_text="Creatinine 1.0",
    )
    assert not normal_obs.is_abnormal()
    assert not normal_obs.is_critical()

    high_obs = LabObservation(
        code_snomed="113075003",
        code_loinc="2160-0",
        display_name="Creatinine",
        numeric_value=2.0,
        unit="mg/dL",
        reference_low=0.7,
        reference_high=1.3,
        flag=ObservationFlag.HIGH,
        observed_at=datetime(2025, 1, 1),
        raw_text="Creatinine 2.0 H",
    )
    assert high_obs.is_abnormal()
    assert not high_obs.is_critical()

    crit_obs = LabObservation(
        code_snomed="113075003",
        code_loinc="2160-0",
        display_name="Potassium",
        numeric_value=6.8,
        unit="mmol/L",
        reference_low=3.5,
        reference_high=5.1,
        flag=ObservationFlag.CRITICAL_HIGH,
        observed_at=datetime(2025, 1, 1),
        raw_text="Potassium 6.8 CRIT",
    )
    assert crit_obs.is_abnormal()
    assert crit_obs.is_critical()


def test_medication_record_status():
    """MedicationRecord correctly filters active vs stopped status."""
    med_active = MedicationRecord(
        code_rxnorm="316049",
        drug_name="Lisinopril 10 MG",
        dosage="10 mg oral daily",
        route="oral",
        status="active",
        started_at=datetime(2024, 6, 1),
    )
    assert med_active.is_active()

    med_stopped = MedicationRecord(
        code_rxnorm="316049",
        drug_name="Lisinopril 10 MG",
        dosage="10 mg oral daily",
        route="oral",
        status="stopped",
        started_at=datetime(2024, 6, 1),
        ended_at=datetime(2024, 12, 1),
    )
    assert not med_stopped.is_active()


def test_condition_status():
    """Condition correctly tracks active states."""
    cond_active = Condition(
        code_snomed="44054006",
        display_name="Type 2 Diabetes Mellitus",
        clinical_status="active",
        onset_date=datetime(2020, 1, 1),
    )
    assert cond_active.is_active()

    cond_resolved = Condition(
        code_snomed="386661006",
        display_name="Fever",
        clinical_status="resolved",
        onset_date=datetime(2024, 1, 1),
        abatement_date=datetime(2024, 1, 5),
    )
    assert not cond_resolved.is_active()


def test_patient_timeline_aggregates():
    """PatientTimeline aggregates encounters, active medications, and critical findings."""
    obs_crit = LabObservation(
        code_snomed="113075003",
        code_loinc="2160-0",
        display_name="Potassium",
        numeric_value=7.0,
        unit="mmol/L",
        reference_low=3.5,
        reference_high=5.1,
        flag=ObservationFlag.CRITICAL_HIGH,
        observed_at=datetime(2025, 2, 1),
        raw_text="Potassium 7.0 CRIT",
    )
    med1 = MedicationRecord(
        code_rxnorm="197361",
        drug_name="Amlodipine 5 MG",
        dosage="5 mg oral daily",
        route="oral",
        status="active",
        started_at=datetime(2024, 1, 1),
    )
    med2 = MedicationRecord(
        code_rxnorm="316049",
        drug_name="Lisinopril 10 MG",
        dosage="10 mg oral daily",
        route="oral",
        status="stopped",
        started_at=datetime(2023, 1, 1),
        ended_at=datetime(2024, 1, 1),
    )

    enc1 = ClinicalEncounter(
        encounter_id="enc-001",
        encounter_type="ambulatory",
        start_time=datetime(2024, 1, 1),
        medications=[med1, med2],
    )
    enc2 = ClinicalEncounter(
        encounter_id="enc-002",
        encounter_type="emergency",
        start_time=datetime(2025, 2, 1),
        observations=[obs_crit],
    )

    timeline = PatientTimeline(
        patient_id=PatientId("pat-100"),
        tenant_id=TenantId("tenant-01"),
        clinic_id=ClinicId("clinic-01"),
        demographics={"age": 62, "gender": Gender.MALE},
        encounters=[enc1, enc2],
        created_at=datetime(2025, 2, 1),
        updated_at=datetime(2025, 2, 1),
    )

    assert timeline.encounter_count() == 2
    assert len(timeline.active_medications()) == 1
    assert timeline.active_medications()[0].drug_name == "Amlodipine 5 MG"
    assert timeline.latest_encounter() == enc2
    assert len(timeline.all_critical_observations()) == 1

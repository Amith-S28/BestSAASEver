"""Integration tests for LanceDB patient timeline repository."""

from datetime import datetime, timezone
import pytest
import shutil

from medrag.domain.exceptions import TenantIsolationViolationException
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
from medrag.infrastructure.storage.timeline_repo import LanceDBTimelineRepository


@pytest.fixture
def temp_timeline_repo(tmp_path):
    """Fixture providing an isolated timeline repository."""
    db_dir = str(tmp_path / "timeline_db")
    repo = LanceDBTimelineRepository(db_uri=db_dir)
    yield repo
    shutil.rmtree(db_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_timeline_roundtrip_persistence(temp_timeline_repo):
    """Timeline repository serializes and deserializes pure domain objects without loss."""
    now = datetime.now(timezone.utc)
    obs = LabObservation(
        code_snomed="113075003",
        code_loinc="2160-0",
        display_name="Serum Creatinine",
        numeric_value=1.8,
        unit="mg/dL",
        reference_low=0.7,
        reference_high=1.3,
        flag=ObservationFlag.HIGH,
        observed_at=now,
        raw_text="Creatinine 1.8 H",
    )
    med = MedicationRecord(
        code_rxnorm="316049",
        drug_name="Lisinopril 10 MG",
        dosage="10 mg oral daily",
        route="oral",
        status="active",
        started_at=now,
    )
    cond = Condition(
        code_snomed="44054006",
        display_name="Type 2 Diabetes",
        clinical_status="active",
        onset_date=now,
    )
    enc = ClinicalEncounter(
        encounter_id="enc-2025-01",
        encounter_type="ambulatory",
        start_time=now,
        chief_complaint="Follow-up on renal panel",
        observations=[obs],
        medications=[med],
        conditions=[cond],
    )
    timeline = PatientTimeline(
        patient_id=PatientId("pat-patient-99"),
        tenant_id=TenantId("tenant-mayo"),
        clinic_id=ClinicId("clinic-nephrology"),
        demographics={"age": 55, "gender": Gender.FEMALE.value},
        encounters=[enc],
        created_at=now,
        updated_at=now,
    )

    # 1. Save
    await temp_timeline_repo.save_timeline(timeline)

    # 2. Retrieve
    retrieved = await temp_timeline_repo.get_timeline("tenant-mayo", PatientId("pat-patient-99"))
    assert retrieved is not None
    assert retrieved.patient_id.value == "pat-patient-99"
    assert retrieved.encounter_count() == 1

    enc_out = retrieved.encounters[0]
    assert enc_out.encounter_id == "enc-2025-01"
    assert len(enc_out.observations) == 1
    assert enc_out.observations[0].numeric_value == 1.8
    assert enc_out.observations[0].flag == ObservationFlag.HIGH
    assert len(enc_out.medications) == 1
    assert enc_out.medications[0].is_active()

    # 3. Cross-tenant isolation: Tenant B cannot access Tenant A's patient
    unauthorized = await temp_timeline_repo.get_timeline("tenant-hopkins", PatientId("pat-patient-99"))
    assert unauthorized is None


@pytest.mark.asyncio
async def test_patient_erasure_and_listing(temp_timeline_repo):
    """Patient deletion purges record under HIPAA Right to Erasure."""
    now = datetime.now(timezone.utc)
    timeline = PatientTimeline(
        patient_id=PatientId("pat-delete-me"),
        tenant_id=TenantId("tenant-test"),
        clinic_id=ClinicId("clinic-general"),
        demographics={"gender": "male"},
        encounters=[],
        created_at=now,
        updated_at=now,
    )
    await temp_timeline_repo.save_timeline(timeline)

    # List verifies presence
    listed = await temp_timeline_repo.list_patients("tenant-test", "clinic-general")
    assert any(p.patient_id.value == "pat-delete-me" for p in listed)

    # Purge patient
    deleted = await temp_timeline_repo.delete_patient("tenant-test", PatientId("pat-delete-me"))
    assert deleted is True

    # Re-query confirms absence
    assert await temp_timeline_repo.get_timeline("tenant-test", PatientId("pat-delete-me")) is None

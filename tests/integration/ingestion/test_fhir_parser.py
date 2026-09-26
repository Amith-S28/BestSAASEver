"""Integration tests for HL7 FHIR R4 parser and timeline builder."""

import json
import pytest

from medrag.domain.exceptions import IngestionCorruptedException, TenantIsolationViolationException
from medrag.domain.patient import ObservationFlag
from medrag.infrastructure.ingestion.fhir_parser import FHIRParser


@pytest.fixture
def fhir_parser():
    return FHIRParser()


def test_fhir_parse_valid_bundle(fhir_parser):
    """Parser converts FHIR R4 bundle into PatientTimeline with encounters and observations."""
    bundle = {
        "resourceType": "Bundle",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "pat-123",
                    "gender": "male",
                    "birthDate": "1975-04-12",
                }
            },
            {
                "resource": {
                    "resourceType": "Encounter",
                    "id": "enc-1",
                    "period": {"start": "2024-05-01T10:00:00Z", "end": "2024-05-01T11:00:00Z"},
                    "class": {"code": "ambulatory"},
                    "reasonCode": [{"text": "Annual physical and renal check"}],
                }
            },
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "obs-1",
                    "code": {
                        "coding": [
                            {"system": "http://loinc.org", "code": "2160-0", "display": "Creatinine"}
                        ],
                        "text": "Creatinine",
                    },
                    "valueQuantity": {"value": 2.4, "unit": "mg/dL"},
                    "referenceRange": [{"low": {"value": 0.7}, "high": {"value": 1.3}}],
                    "interpretation": [{"coding": [{"code": "HH"}]}],
                    "encounter": {"reference": "Encounter/enc-1"},
                }
            },
            {
                "resource": {
                    "resourceType": "MedicationRequest",
                    "id": "med-1",
                    "medicationCodeableConcept": {
                        "coding": [
                            {"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "316049", "display": "Lisinopril"}
                        ],
                        "text": "Lisinopril 10 MG",
                    },
                    "dosageInstruction": [{"text": "10mg oral daily"}],
                    "status": "active",
                    "encounter": {"reference": "Encounter/enc-1"},
                }
            },
            {
                "resource": {
                    "resourceType": "Condition",
                    "id": "cond-1",
                    "code": {
                        "coding": [
                            {"system": "http://snomed.info/sct", "code": "14669001", "display": "Acute kidney injury"}
                        ],
                        "text": "Acute kidney injury",
                    },
                    "clinicalStatus": {"coding": [{"code": "active"}]},
                    "encounter": {"reference": "Encounter/enc-1"},
                }
            },
        ],
    }

    timeline = fhir_parser.parse_bundle(bundle, tenant_id="tenant-mayo", clinic_id="clinic-renal")

    assert timeline.patient_id.value == "pat-123"
    assert timeline.tenant_id.value == "tenant-mayo"
    assert timeline.clinic_id.value == "clinic-renal"
    assert timeline.demographics["birth_year"] == "1975"
    assert timeline.encounter_count() == 1

    enc = timeline.encounters[0]
    assert enc.encounter_id == "enc-1"
    assert enc.encounter_type == "ambulatory"
    assert len(enc.observations) == 1
    assert enc.observations[0].code_loinc == "2160-0"
    assert enc.observations[0].numeric_value == 2.4
    assert enc.observations[0].flag == ObservationFlag.CRITICAL_HIGH
    assert len(enc.medications) == 1
    assert enc.medications[0].code_rxnorm == "316049"
    assert len(enc.conditions) == 1
    assert enc.conditions[0].code_snomed == "14669001"


def test_fhir_merge_timelines_concurrent_dedup(fhir_parser):
    """Merging timelines deduplicates encounters by ID and appends new ones (Amendment 5)."""
    bundle1 = {
        "resourceType": "Bundle",
        "entry": [
            {"resource": {"resourceType": "Patient", "id": "pat-merge-1"}},
            {
                "resource": {
                    "resourceType": "Encounter",
                    "id": "enc-initial",
                    "period": {"start": "2024-01-01T08:00:00Z"},
                    "reasonCode": [{"text": "First visit"}],
                }
            },
        ],
    }
    bundle2 = {
        "resourceType": "Bundle",
        "entry": [
            {"resource": {"resourceType": "Patient", "id": "pat-merge-1"}},
            {
                "resource": {
                    "resourceType": "Encounter",
                    "id": "enc-initial",
                    "period": {"start": "2024-01-01T08:00:00Z"},
                    "reasonCode": [{"text": "First visit updated"}],
                }
            },
            {
                "resource": {
                    "resourceType": "Encounter",
                    "id": "enc-subsequent",
                    "period": {"start": "2024-06-01T08:00:00Z"},
                    "reasonCode": [{"text": "Second visit"}],
                }
            },
        ],
    }

    timeline1 = fhir_parser.parse_bundle(bundle1, "tenant-test", "clinic-test")
    timeline2 = fhir_parser.parse_bundle(bundle2, "tenant-test", "clinic-test")

    merged = fhir_parser.merge_timelines(timeline1, timeline2)

    # Encounter enc-initial must be deduplicated; enc-subsequent appended -> total 2
    assert merged.encounter_count() == 2
    assert [e.encounter_id for e in merged.encounters] == ["enc-initial", "enc-subsequent"]
    assert merged.encounters[0].chief_complaint == "First visit updated"


def test_fhir_parse_malformed_syntax(fhir_parser):
    """Malformed bundle triggers IngestionCorruptedException."""
    with pytest.raises(IngestionCorruptedException):
        fhir_parser.parse_bundle("not-json", "tenant-test", "clinic-test")

    with pytest.raises(IngestionCorruptedException):
        fhir_parser.parse_bundle({"resourceType": "NotBundle"}, "tenant-test", "clinic-test")

    with pytest.raises(TenantIsolationViolationException):
        fhir_parser.parse_bundle({"resourceType": "Bundle", "entry": []}, "", "clinic-test")

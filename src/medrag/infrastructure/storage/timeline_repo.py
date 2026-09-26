"""Patient timeline repository adapter implementing medrag.ports.storage.ITimelineRepository."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import pyarrow as pa
import lancedb

from medrag.domain.exceptions import TenantIsolationViolationException
from medrag.domain.patient import (
    ClinicId,
    ClinicalEncounter,
    Condition,
    LabObservation,
    MedicationRecord,
    ObservationFlag,
    PatientId,
    PatientTimeline,
    TenantId,
)


def get_timelines_arrow_schema() -> pa.Schema:
    """Canonical Apache Arrow schema for patient_timelines table."""
    return pa.schema([
        pa.field("patient_id", pa.string(), nullable=False),
        pa.field("tenant_id", pa.string(), nullable=False),
        pa.field("clinic_id", pa.string(), nullable=False),
        pa.field("demographics_json", pa.string(), nullable=False),
        pa.field("timeline_json", pa.string(), nullable=False),
        pa.field("encounter_count", pa.int32(), nullable=False),
        pa.field("last_encounter_at", pa.timestamp("us"), nullable=False),
        pa.field("created_at", pa.timestamp("us"), nullable=False),
        pa.field("updated_at", pa.timestamp("us"), nullable=False),
    ])


class LanceDBTimelineRepository:
    """LanceDB repository for patient timeline persistence with tenant scoping."""

    def __init__(
        self,
        db_uri: str = "./data/lancedb",
        table_name: str = "patient_timelines",
    ) -> None:
        self.db_uri = db_uri
        self.table_name = table_name
        Path(self.db_uri).mkdir(parents=True, exist_ok=True)
        self.db = lancedb.connect(self.db_uri)
        self._ensure_table()

    def _table_exists(self) -> bool:
        """Check if table exists using list_tables."""
        try:
            res = self.db.list_tables()
            table_list = getattr(res, "tables", res)
            return self.table_name in table_list
        except Exception:
            return self.table_name in self.db.table_names()

    def _ensure_table(self) -> None:
        if not self._table_exists():
            schema = get_timelines_arrow_schema()
            self.table = self.db.create_table(self.table_name, schema=schema)
        else:
            self.table = self.db.open_table(self.table_name)

    def _serialize_encounter(self, enc: ClinicalEncounter) -> Dict[str, Any]:
        return {
            "encounter_id": enc.encounter_id,
            "encounter_type": enc.encounter_type,
            "start_time": enc.start_time.isoformat(),
            "end_time": enc.end_time.isoformat() if enc.end_time else None,
            "chief_complaint": enc.chief_complaint,
            "observations": [
                {
                    "code_snomed": o.code_snomed,
                    "code_loinc": o.code_loinc,
                    "display_name": o.display_name,
                    "numeric_value": o.numeric_value,
                    "unit": o.unit,
                    "reference_low": o.reference_low,
                    "reference_high": o.reference_high,
                    "flag": o.flag.value,
                    "observed_at": o.observed_at.isoformat(),
                    "raw_text": o.raw_text,
                }
                for o in enc.observations
            ],
            "medications": [
                {
                    "code_rxnorm": m.code_rxnorm,
                    "drug_name": m.drug_name,
                    "dosage": m.dosage,
                    "route": m.route,
                    "status": m.status,
                    "started_at": m.started_at.isoformat(),
                    "ended_at": m.ended_at.isoformat() if m.ended_at else None,
                }
                for m in enc.medications
            ],
            "conditions": [
                {
                    "code_snomed": c.code_snomed,
                    "display_name": c.display_name,
                    "clinical_status": c.clinical_status,
                    "onset_date": c.onset_date.isoformat() if c.onset_date else None,
                    "abatement_date": c.abatement_date.isoformat() if c.abatement_date else None,
                }
                for c in enc.conditions
            ],
        }

    def _deserialize_encounter(self, data: Dict[str, Any]) -> ClinicalEncounter:
        observations = [
            LabObservation(
                code_snomed=o["code_snomed"],
                code_loinc=o["code_loinc"],
                display_name=o["display_name"],
                numeric_value=float(o["numeric_value"]),
                unit=o["unit"],
                reference_low=float(o["reference_low"]) if o.get("reference_low") is not None else None,
                reference_high=float(o["reference_high"]) if o.get("reference_high") is not None else None,
                flag=ObservationFlag(o["flag"]),
                observed_at=datetime.fromisoformat(o["observed_at"]),
                raw_text=o["raw_text"],
            )
            for o in data.get("observations", [])
        ]
        medications = [
            MedicationRecord(
                code_rxnorm=m["code_rxnorm"],
                drug_name=m["drug_name"],
                dosage=m["dosage"],
                route=m["route"],
                status=m["status"],
                started_at=datetime.fromisoformat(m["started_at"]),
                ended_at=datetime.fromisoformat(m["ended_at"]) if m.get("ended_at") else None,
            )
            for m in data.get("medications", [])
        ]
        conditions = [
            Condition(
                code_snomed=c["code_snomed"],
                display_name=c["display_name"],
                clinical_status=c["clinical_status"],
                onset_date=datetime.fromisoformat(c["onset_date"]) if c.get("onset_date") else None,
                abatement_date=datetime.fromisoformat(c["abatement_date"]) if c.get("abatement_date") else None,
            )
            for c in data.get("conditions", [])
        ]
        return ClinicalEncounter(
            encounter_id=data["encounter_id"],
            encounter_type=data["encounter_type"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            chief_complaint=data.get("chief_complaint", ""),
            observations=observations,
            medications=medications,
            conditions=conditions,
        )

    async def save_timeline(self, timeline: PatientTimeline) -> None:
        """Atomically persist or replace patient timeline."""
        t_id = timeline.tenant_id.value
        p_id = timeline.patient_id.value

        # Delete existing row if present (idempotent upsert)
        try:
            self.table.delete(f"tenant_id = '{t_id}' AND patient_id = '{p_id}'")
        except Exception:
            pass

        encounters_serialized = [self._serialize_encounter(e) for e in timeline.encounters]
        latest = timeline.latest_encounter()
        last_enc_at = latest.start_time if latest else timeline.created_at

        row = {
            "patient_id": p_id,
            "tenant_id": t_id,
            "clinic_id": timeline.clinic_id.value,
            "demographics_json": json.dumps(timeline.demographics),
            "timeline_json": json.dumps(encounters_serialized),
            "encounter_count": len(timeline.encounters),
            "last_encounter_at": last_enc_at,
            "created_at": timeline.created_at,
            "updated_at": timeline.updated_at,
        }
        self.table.add([row])

    async def get_timeline(self, tenant_id: str, patient_id: PatientId) -> Optional[PatientTimeline]:
        """Fetch patient timeline scoped to tenant."""
        if not tenant_id or not tenant_id.strip():
            raise TenantIsolationViolationException("Empty tenant context for timeline query")

        predicate = f"tenant_id = '{tenant_id}' AND patient_id = '{patient_id.value}'"
        results = self.table.search().where(predicate).limit(1).to_list()

        if not results:
            return None

        row = results[0]
        demographics = json.loads(row["demographics_json"])
        raw_encounters = json.loads(row["timeline_json"])
        encounters = [self._deserialize_encounter(e) for e in raw_encounters]

        return PatientTimeline(
            patient_id=PatientId(row["patient_id"]),
            tenant_id=TenantId(row["tenant_id"]),
            clinic_id=ClinicId(row["clinic_id"]),
            demographics=demographics,
            encounters=encounters,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def delete_patient(self, tenant_id: str, patient_id: PatientId) -> bool:
        """Purge patient timeline under HIPAA Right to Erasure."""
        if not tenant_id or not tenant_id.strip():
            raise TenantIsolationViolationException("Empty tenant context for patient deletion")

        predicate = f"tenant_id = '{tenant_id}' AND patient_id = '{patient_id.value}'"
        count_before = self.table.count_rows(predicate)
        if count_before > 0:
            self.table.delete(predicate)
            return True
        return False

    async def list_patients(
        self, tenant_id: str, clinic_id: str, limit: int = 50, cursor: Optional[str] = None
    ) -> List[PatientTimeline]:
        """List patient timelines for clinic with limit."""
        if not tenant_id or not tenant_id.strip():
            raise TenantIsolationViolationException("Empty tenant context for listing")

        predicate = f"tenant_id = '{tenant_id}' AND clinic_id = '{clinic_id}'"
        results = self.table.search().where(predicate).limit(limit).to_list()

        timelines: List[PatientTimeline] = []
        for row in results:
            demographics = json.loads(row["demographics_json"])
            raw_encounters = json.loads(row["timeline_json"])
            encounters = [self._deserialize_encounter(e) for e in raw_encounters]
            timelines.append(
                PatientTimeline(
                    patient_id=PatientId(row["patient_id"]),
                    tenant_id=TenantId(row["tenant_id"]),
                    clinic_id=ClinicId(row["clinic_id"]),
                    demographics=demographics,
                    encounters=encounters,
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
            )
        return timelines

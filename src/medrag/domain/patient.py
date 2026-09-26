"""Pure domain models for patients, encounters, observations, and timelines.

ZERO external dependencies. Python standard library only.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNKNOWN = "unknown"


class ObservationFlag(str, Enum):
    NORMAL = "normal"
    HIGH = "high"
    LOW = "low"
    CRITICAL_HIGH = "critical_high"
    CRITICAL_LOW = "critical_low"


@dataclass(frozen=True)
class PatientId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("PatientId cannot be empty or whitespace")


@dataclass(frozen=True)
class TenantId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("TenantId cannot be empty or whitespace")


@dataclass(frozen=True)
class ClinicId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("ClinicId cannot be empty or whitespace")


@dataclass(frozen=True)
class LabObservation:
    code_snomed: str
    code_loinc: str
    display_name: str
    numeric_value: float
    unit: str
    reference_low: Optional[float]
    reference_high: Optional[float]
    flag: ObservationFlag
    observed_at: datetime
    raw_text: str

    def is_abnormal(self) -> bool:
        return self.flag != ObservationFlag.NORMAL

    def is_critical(self) -> bool:
        return self.flag in (ObservationFlag.CRITICAL_HIGH, ObservationFlag.CRITICAL_LOW)


@dataclass(frozen=True)
class MedicationRecord:
    code_rxnorm: str
    drug_name: str
    dosage: str
    route: str
    status: str  # active | completed | stopped | entered-in-error
    started_at: datetime
    ended_at: Optional[datetime] = None

    def is_active(self) -> bool:
        return self.status == "active"


@dataclass(frozen=True)
class Condition:
    code_snomed: str
    display_name: str
    clinical_status: str  # active | recurrence | relapse | inactive | remission | resolved
    onset_date: Optional[datetime] = None
    abatement_date: Optional[datetime] = None

    def is_active(self) -> bool:
        return self.clinical_status in ("active", "recurrence", "relapse")


@dataclass(frozen=True)
class ClinicalEncounter:
    encounter_id: str
    encounter_type: str  # ambulatory | emergency | inpatient | observation
    start_time: datetime
    end_time: Optional[datetime] = None
    chief_complaint: str = ""
    observations: List[LabObservation] = field(default_factory=list)
    medications: List[MedicationRecord] = field(default_factory=list)
    conditions: List[Condition] = field(default_factory=list)

    def critical_observations(self) -> List[LabObservation]:
        return [obs for obs in self.observations if obs.is_critical()]

    def abnormal_observations(self) -> List[LabObservation]:
        return [obs for obs in self.observations if obs.is_abnormal()]


@dataclass(frozen=True)
class PatientTimeline:
    patient_id: PatientId
    tenant_id: TenantId
    clinic_id: ClinicId
    demographics: Dict[str, Any]
    encounters: List[ClinicalEncounter]
    created_at: datetime
    updated_at: datetime

    def encounter_count(self) -> int:
        return len(self.encounters)

    def active_medications(self) -> List[MedicationRecord]:
        active_meds: List[MedicationRecord] = []
        for encounter in self.encounters:
            active_meds.extend([m for m in encounter.medications if m.is_active()])
        return active_meds

    def latest_encounter(self) -> Optional[ClinicalEncounter]:
        if not self.encounters:
            return None
        return max(self.encounters, key=lambda enc: enc.start_time)

    def all_critical_observations(self) -> List[LabObservation]:
        crit: List[LabObservation] = []
        for encounter in self.encounters:
            crit.extend(encounter.critical_observations())
        return crit

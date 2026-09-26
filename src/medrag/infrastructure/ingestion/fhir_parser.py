"""HL7 FHIR R4 Bundle Parser and Longitudinal Timeline Builder."""

from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional, Union

from medrag.domain.exceptions import (
    IngestionCorruptedException,
    InvalidFHIRResourceException,
    TenantIsolationViolationException,
)
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


class FHIRParser:
    """Parser converting HL7 FHIR R4 JSON bundles into immutable domain PatientTimeline aggregates."""

    @staticmethod
    def _map_flag(interpretation_code: Optional[str], val: float, low: Optional[float], high: Optional[float]) -> ObservationFlag:
        """Map FHIR interpretation code or numeric bounds to ObservationFlag."""
        if interpretation_code:
            code = interpretation_code.upper()
            if code in ("CH", "CRIT_H", "CRITICAL_HIGH", "HH"):
                return ObservationFlag.CRITICAL_HIGH
            if code in ("CL", "CRIT_L", "CRITICAL_LOW", "LL"):
                return ObservationFlag.CRITICAL_LOW
            if code in ("H", "HIGH", "A", "ABNORMAL"):
                return ObservationFlag.HIGH
            if code in ("L", "LOW"):
                return ObservationFlag.LOW

        # Derivation from reference ranges if code absent
        if low is not None and val < low:
            if val < low * 0.7:  # Severe threshold
                return ObservationFlag.CRITICAL_LOW
            return ObservationFlag.LOW
        if high is not None and val > high:
            if val > high * 1.5:  # Severe threshold
                return ObservationFlag.CRITICAL_HIGH
            return ObservationFlag.HIGH

        return ObservationFlag.NORMAL

    @staticmethod
    def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO-8601 clinical date-time string."""
        if not dt_str:
            return None
        try:
            # Handle date only (YYYY-MM-DD)
            if len(dt_str) == 10:
                return datetime.strptime(dt_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            # Handle standard ISO format
            clean_str = dt_str.replace("Z", "+00:00")
            return datetime.fromisoformat(clean_str)
        except Exception:
            return None

    def parse_bundle(
        self,
        bundle_input: Union[str, Dict[str, Any]],
        tenant_id: str,
        clinic_id: str,
        filename: str = "bundle.json",
    ) -> PatientTimeline:
        """Parse FHIR R4 Bundle JSON into a domain PatientTimeline aggregate root."""
        if not tenant_id or not tenant_id.strip():
            raise TenantIsolationViolationException("Empty tenant context for FHIR parsing")

        if isinstance(bundle_input, str):
            try:
                bundle = json.loads(bundle_input)
            except Exception as e:
                raise IngestionCorruptedException(filename, f"Invalid JSON syntax: {e}")
        else:
            bundle = bundle_input

        if not isinstance(bundle, dict):
            raise IngestionCorruptedException(filename, "Bundle payload must be a JSON object")

        resource_type = bundle.get("resourceType")
        if resource_type != "Bundle":
            raise IngestionCorruptedException(
                filename, f"Expected resourceType 'Bundle', got '{resource_type}'"
            )

        entries = bundle.get("entry", [])
        if not isinstance(entries, list):
            raise IngestionCorruptedException(filename, "Bundle 'entry' field must be an array")

        # Extraction containers
        patient_id_val: Optional[str] = None
        demographics: Dict[str, Any] = {}
        encounters_by_id: Dict[str, ClinicalEncounter] = {}
        observations_unbound: List[LabObservation] = []
        medications_unbound: List[MedicationRecord] = []
        conditions_unbound: List[Condition] = []
        now = datetime.now(timezone.utc)

        # 1. First pass: Extract Patient and Encounters
        for i, entry in enumerate(entries):
            resource = entry.get("resource", {})
            r_type = resource.get("resourceType")
            r_id = resource.get("id")

            if r_type == "Patient":
                patient_id_val = r_id
                demographics = {
                    "gender": resource.get("gender", Gender.UNKNOWN.value),
                    "birth_year": (
                        resource.get("birthDate", "").split("-")[0]
                        if resource.get("birthDate")
                        else None
                    ),
                    "marital_status": (
                        resource.get("maritalStatus", {}).get("text")
                        if isinstance(resource.get("maritalStatus"), dict)
                        else None
                    ),
                }

            elif r_type == "Encounter":
                if not r_id:
                    continue
                period = resource.get("period", {})
                start_dt = self._parse_datetime(period.get("start")) or now
                end_dt = self._parse_datetime(period.get("end"))

                encounter_type = "ambulatory"
                enc_class = resource.get("class", {})
                if isinstance(enc_class, dict) and enc_class.get("code"):
                    encounter_type = enc_class["code"].lower()

                reason_text = ""
                reasons = resource.get("reasonCode", [])
                if reasons and isinstance(reasons[0], dict):
                    reason_text = reasons[0].get("text", "")

                encounters_by_id[r_id] = ClinicalEncounter(
                    encounter_id=r_id,
                    encounter_type=encounter_type,
                    start_time=start_dt,
                    end_time=end_dt,
                    chief_complaint=reason_text,
                    observations=[],
                    medications=[],
                    conditions=[],
                )

        # Ensure fallback patient id if not explicitly in bundle Patient resource
        if not patient_id_val:
            patient_id_val = "pat-synthetic-default"

        # 2. Second pass: Parse Observations, Medications, and Conditions
        for entry in entries:
            resource = entry.get("resource", {})
            r_type = resource.get("resourceType")

            # --- LabObservation ---
            if r_type == "Observation":
                code_obj = resource.get("code", {})
                codings = code_obj.get("coding", [])
                loinc_code = ""
                snomed_code = ""
                display_name = code_obj.get("text", "Clinical Observation")

                for c in codings:
                    sys_url = c.get("system", "")
                    c_code = c.get("code", "")
                    if "loinc" in sys_url.lower():
                        loinc_code = c_code
                    elif "snomed" in sys_url.lower():
                        snomed_code = c_code
                    if c.get("display"):
                        display_name = c["display"]

                # Extract numeric value & unit
                val_quantity = resource.get("valueQuantity", {})
                if isinstance(val_quantity, dict) and "value" in val_quantity:
                    try:
                        numeric_val = float(val_quantity["value"])
                    except (ValueError, TypeError):
                        numeric_val = 0.0
                    unit = val_quantity.get("unit", "")
                else:
                    numeric_val = 0.0
                    unit = ""

                # Reference range
                ref_low: Optional[float] = None
                ref_high: Optional[float] = None
                ref_ranges = resource.get("referenceRange", [])
                if ref_ranges and isinstance(ref_ranges[0], dict):
                    low_dict = ref_ranges[0].get("low", {})
                    high_dict = ref_ranges[0].get("high", {})
                    if "value" in low_dict:
                        ref_low = float(low_dict["value"])
                    if "value" in high_dict:
                        ref_high = float(high_dict["value"])

                # Interpretation
                interp = resource.get("interpretation", [])
                interp_code = None
                if interp and isinstance(interp[0], dict):
                    interp_coding = interp[0].get("coding", [])
                    if interp_coding:
                        interp_code = interp_coding[0].get("code")

                flag = self._map_flag(interp_code, numeric_val, ref_low, ref_high)
                obs_dt = (
                    self._parse_datetime(resource.get("effectiveDateTime"))
                    or self._parse_datetime(resource.get("issued"))
                    or now
                )

                obs = LabObservation(
                    code_snomed=snomed_code,
                    code_loinc=loinc_code,
                    display_name=display_name,
                    numeric_value=numeric_val,
                    unit=unit,
                    reference_low=ref_low,
                    reference_high=ref_high,
                    flag=flag,
                    observed_at=obs_dt,
                    raw_text=f"{display_name} {numeric_val} {unit}".strip(),
                )

                # Bind to encounter if reference exists
                enc_ref = resource.get("encounter", {}).get("reference", "")
                enc_id = enc_ref.split("/")[-1] if "/" in enc_ref else enc_ref
                if enc_id in encounters_by_id:
                    enc = encounters_by_id[enc_id]
                    enc.observations.append(obs)
                else:
                    observations_unbound.append(obs)

            # --- MedicationRecord ---
            elif r_type == "MedicationRequest":
                med_codeable = resource.get("medicationCodeableConcept", {})
                rx_codings = med_codeable.get("coding", [])
                rx_code = ""
                drug_name = med_codeable.get("text", "Medication")

                for c in rx_codings:
                    if "rxnorm" in c.get("system", "").lower():
                        rx_code = c.get("code", "")
                    if c.get("display"):
                        drug_name = c["display"]

                dosage = "Standard dose"
                dosage_inst = resource.get("dosageInstruction", [])
                if dosage_inst and isinstance(dosage_inst[0], dict):
                    dosage = dosage_inst[0].get("text", dosage)

                status = resource.get("status", "active")
                authored_dt = self._parse_datetime(resource.get("authoredOn")) or now

                med = MedicationRecord(
                    code_rxnorm=rx_code,
                    drug_name=drug_name,
                    dosage=dosage,
                    route="oral",
                    status=status,
                    started_at=authored_dt,
                )

                enc_ref = resource.get("encounter", {}).get("reference", "")
                enc_id = enc_ref.split("/")[-1] if "/" in enc_ref else enc_ref
                if enc_id in encounters_by_id:
                    enc = encounters_by_id[enc_id]
                    enc.medications.append(med)
                else:
                    medications_unbound.append(med)

            # --- Condition ---
            elif r_type == "Condition":
                code_obj = resource.get("code", {})
                cond_codings = code_obj.get("coding", [])
                snomed_code = ""
                display_name = code_obj.get("text", "Condition")

                for c in cond_codings:
                    if "snomed" in c.get("system", "").lower():
                        snomed_code = c.get("code", "")
                    if c.get("display"):
                        display_name = c["display"]

                clinical_status = "active"
                c_status_obj = resource.get("clinicalStatus", {})
                if isinstance(c_status_obj, dict):
                    codings = c_status_obj.get("coding", [])
                    if codings:
                        clinical_status = codings[0].get("code", "active")

                onset_dt = self._parse_datetime(resource.get("onsetDateTime")) or now

                cond = Condition(
                    code_snomed=snomed_code,
                    display_name=display_name,
                    clinical_status=clinical_status,
                    onset_date=onset_dt,
                )

                enc_ref = resource.get("encounter", {}).get("reference", "")
                enc_id = enc_ref.split("/")[-1] if "/" in enc_ref else enc_ref
                if enc_id in encounters_by_id:
                    enc = encounters_by_id[enc_id]
                    enc.conditions.append(cond)
                else:
                    conditions_unbound.append(cond)

        # 3. If encounters exist but some resources were unbound, bind them to latest or default encounter
        if encounters_by_id:
            all_encounters = list(encounters_by_id.values())
            latest_enc = max(all_encounters, key=lambda e: e.start_time)
            latest_enc.observations.extend(observations_unbound)
            latest_enc.medications.extend(medications_unbound)
            latest_enc.conditions.extend(conditions_unbound)
        else:
            # Synthetic encounter for bundle with observations but no explicit Encounter resource
            default_enc = ClinicalEncounter(
                encounter_id="enc-inferred-001",
                encounter_type="ambulatory",
                start_time=now,
                chief_complaint="Clinical observations recorded",
                observations=observations_unbound,
                medications=medications_unbound,
                conditions=conditions_unbound,
            )
            all_encounters = [default_enc]

        # Sort encounters chronologically
        all_encounters.sort(key=lambda e: e.start_time)

        return PatientTimeline(
            patient_id=PatientId(patient_id_val),
            tenant_id=TenantId(tenant_id),
            clinic_id=ClinicId(clinic_id),
            demographics=demographics,
            encounters=all_encounters,
            created_at=now,
            updated_at=now,
        )

    def merge_timelines(
        self, existing: PatientTimeline, incoming: PatientTimeline
    ) -> PatientTimeline:
        """Merge two timelines for the same patient following Last-Write-Wins and encounter deduplication."""
        if existing.patient_id != incoming.patient_id:
            raise ValueError("Cannot merge timelines for different patient IDs")

        encounters_map: Dict[str, ClinicalEncounter] = {
            enc.encounter_id: enc for enc in existing.encounters
        }

        for incoming_enc in incoming.encounters:
            # Overwrite or append encounter by encounter_id
            encounters_map[incoming_enc.encounter_id] = incoming_enc

        merged_encounters = sorted(encounters_map.values(), key=lambda e: e.start_time)
        now = datetime.now(timezone.utc)

        merged_demographics = {**existing.demographics, **incoming.demographics}

        return PatientTimeline(
            patient_id=existing.patient_id,
            tenant_id=existing.tenant_id,
            clinic_id=existing.clinic_id,
            demographics=merged_demographics,
            encounters=merged_encounters,
            created_at=existing.created_at,
            updated_at=now,
        )

"""Patient Management and Ingestion API routes."""

import base64
import json
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, Request, UploadFile
from pydantic import BaseModel, Field
from medrag.domain.exceptions import ClinicalException, IngestionCorruptedException, PatientNotFoundException
from medrag.domain.patient import PatientId
from medrag.interfaces.api.dependencies import (
    assert_tenant_boundary,
    get_services,
    require_scope,
)
from medrag.ports.auth import AuthenticatedUser

router = APIRouter(prefix="/api/v1/patients", tags=["Patient Management"])


@router.post("/ingest/fhir")
async def ingest_fhir_bundle(
    request: Request,
    user: AuthenticatedUser = Depends(require_scope("patient:write")),
):
    """Upload and ingest FHIR R4 JSON bundle into structured timeline."""
    services = get_services()
    try:
        body = await request.json()
    except Exception as e:
        raise IngestionCorruptedException("fhir_payload.json", f"Invalid JSON: {str(e)}")

    if not isinstance(body, dict) or body.get("resourceType") != "Bundle":
        raise IngestionCorruptedException("fhir_payload.json", "Root resource must be a FHIR Bundle")

    # Extract patient ID from bundle if present
    patient_id = "pat-unknown"
    for entry in body.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Patient":
            patient_id = resource.get("id", "pat-unknown")
            break

    # Enqueue background ingestion job
    job_id = await services.job_queue.enqueue(
        job_type="INGEST_FHIR",
        payload={"bundle": body, "patient_id": patient_id},
        tenant_id=user.tenant_id,
    )

    services.audit_log_repo.record_event(
        event_type="patient.ingest_queued",
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        role=user.role,
        resource_type="patient",
        resource_id=patient_id,
        details={"job_id": job_id, "format": "fhir_r4"},
        trace_id=getattr(request.state, "trace_id", "trace-ingest"),
    )

    return {
        "job_id": job_id,
        "patient_id": patient_id,
        "status": "queued",
        "message": "FHIR R4 bundle queued for ingestion",
    }


@router.post("/ingest/pdf")
async def ingest_pdf_report(
    file: UploadFile = File(...),
    patient_id: Optional[str] = None,
    user: AuthenticatedUser = Depends(require_scope("patient:write")),
    request: Request = None,
):
    """Upload and ingest diagnostic PDF report."""
    services = get_services()
    content = await file.read()
    if not content:
        raise IngestionCorruptedException(file.filename or "report.pdf", "Empty file provided")

    pid = patient_id or f"pat-{uuid.uuid4().hex[:8]}"

    job_id = await services.job_queue.enqueue(
        job_type="INGEST_PDF",
        payload={
            "filename": file.filename,
            "data_b64": base64.b64encode(content).decode("utf-8"),
            "patient_id": pid,
        },
        tenant_id=user.tenant_id,
    )

    trace_id = getattr(request.state, "trace_id", "trace-pdf") if request else "trace-pdf"
    services.audit_log_repo.record_event(
        event_type="patient.pdf_ingest_queued",
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        role=user.role,
        resource_type="patient",
        resource_id=pid,
        details={"job_id": job_id, "filename": file.filename},
        trace_id=trace_id,
    )

    return {
        "job_id": job_id,
        "patient_id": pid,
        "status": "queued",
        "filename": file.filename,
    }


@router.get("")
async def list_patients(
    limit: int = 25,
    cursor: Optional[str] = None,
    user: AuthenticatedUser = Depends(require_scope("patient:read")),
):
    """List patient summaries for current tenant with cursor-based pagination."""
    services = get_services()
    clinic_id = user.clinic_id or "default"
    timelines = await services.timeline_repo.list_patients(
        tenant_id=user.tenant_id, clinic_id=clinic_id, limit=limit, cursor=cursor
    )
    items = [
        {
            "patient_id": t.patient_id.value if hasattr(t.patient_id, "value") else str(t.patient_id),
            "tenant_id": t.tenant_id.value if hasattr(t.tenant_id, "value") else str(t.tenant_id),
            "clinic_id": t.clinic_id.value if hasattr(t.clinic_id, "value") else str(t.clinic_id),
            "demographics": t.demographics,
            "encounter_count": len(t.encounters),
            "created_at": t.created_at.isoformat() if hasattr(t.created_at, "isoformat") else str(t.created_at),
            "updated_at": t.updated_at.isoformat() if hasattr(t.updated_at, "isoformat") else str(t.updated_at),
        }
        for t in timelines
    ]
    return {
        "items": items,
        "total_count": len(items),
        "cursor": None,
        "has_more": False,
    }


@router.get("/{patient_id}/timeline")
async def get_patient_timeline(
    patient_id: str,
    user: AuthenticatedUser = Depends(require_scope("patient:read")),
):
    """Retrieve structured longitudinal patient timeline."""
    services = get_services()
    timeline = await services.timeline_repo.get_timeline(user.tenant_id, PatientId(patient_id))
    if not timeline:
        raise PatientNotFoundException(patient_id)

    tenant_val = timeline.tenant_id.value if hasattr(timeline.tenant_id, "value") else str(timeline.tenant_id)
    assert_tenant_boundary(user, tenant_val)

    return {
        "patient_id": timeline.patient_id.value if hasattr(timeline.patient_id, "value") else str(timeline.patient_id),
        "tenant_id": tenant_val,
        "clinic_id": timeline.clinic_id.value if hasattr(timeline.clinic_id, "value") else str(timeline.clinic_id),
        "demographics": timeline.demographics,
        "encounters": [
            {
                "encounter_id": e.encounter_id,
                "encounter_type": e.encounter_type,
                "start_time": e.start_time.isoformat() if hasattr(e.start_time, "isoformat") else str(e.start_time),
                "end_time": e.end_time.isoformat() if e.end_time and hasattr(e.end_time, "isoformat") else None,
                "chief_complaint": e.chief_complaint,
                "conditions": [
                    {
                        "code_icd10": getattr(c, "code_icd10", ""),
                        "code_snomed": getattr(c, "code_snomed", ""),
                        "display_name": getattr(c, "display_name", ""),
                        "clinical_status": getattr(c, "clinical_status", ""),
                    }
                    for c in e.conditions
                ],
                "observations": [
                    {
                        "code_snomed": getattr(o, "code_snomed", ""),
                        "code_loinc": getattr(o, "code_loinc", ""),
                        "display_name": getattr(o, "display_name", ""),
                        "numeric_value": getattr(o, "numeric_value", 0.0),
                        "unit": getattr(o, "unit", ""),
                        "reference_range_low": getattr(o, "reference_range_low", 0.0),
                        "reference_range_high": getattr(o, "reference_range_high", 0.0),
                        "flag": o.flag.value if hasattr(o.flag, "value") else str(o.flag),
                        "is_abnormal": o.is_abnormal() if hasattr(o, "is_abnormal") else False,
                        "is_critical": o.is_critical() if hasattr(o, "is_critical") else False,
                    }
                    for o in e.observations
                ],
                "medications": [
                    {
                        "name": getattr(m, "name", ""),
                        "rxnorm_code": getattr(m, "rxnorm_code", ""),
                        "dosage": getattr(m, "dosage", ""),
                        "route": getattr(m, "route", ""),
                        "frequency": getattr(m, "frequency", ""),
                        "status": m.status.value if hasattr(m.status, "value") else str(m.status),
                    }
                    for m in e.medications
                ],
            }
            for e in timeline.encounters
        ],
        "created_at": timeline.created_at.isoformat() if hasattr(timeline.created_at, "isoformat") else str(timeline.created_at),
        "updated_at": timeline.updated_at.isoformat() if hasattr(timeline.updated_at, "isoformat") else str(timeline.updated_at),
    }


@router.delete("/{patient_id}")
async def delete_patient(
    patient_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(require_scope("patient:delete")),
):
    """Right to erasure: purge patient timeline and associated diagnostic data."""
    services = get_services()
    timeline = await services.timeline_repo.get_timeline(user.tenant_id, patient_id)
    if not timeline:
        raise PatientNotFoundException(patient_id)

    assert_tenant_boundary(user, timeline.tenant_id)

    # Purge timeline
    await services.timeline_repo.delete_timeline(user.tenant_id, patient_id)

    trace_id = getattr(request.state, "trace_id", "trace-delete")
    services.audit_log_repo.record_event(
        event_type="patient.deleted",
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        role=user.role,
        resource_type="patient",
        resource_id=patient_id,
        details={"reason": "Right to erasure / patient deletion requested"},
        trace_id=trace_id,
    )

    return {
        "status": "purged",
        "patient_id": patient_id,
        "message": f"Patient '{patient_id}' data successfully purged under data privacy regulations.",
    }

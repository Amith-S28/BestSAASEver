"""Patient Management and Ingestion API routes."""

import base64
import json
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, Request, UploadFile
from pydantic import BaseModel, Field
from medrag.domain.exceptions import ClinicalException, IngestionCorruptedException, PatientNotFoundException
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
    timelines = await services.timeline_repo.list_timelines(user.tenant_id, limit=limit)
    items = [
        {
            "patient_id": t.patient_id,
            "tenant_id": t.tenant_id,
            "encounter_count": len(t.encounters),
            "created_at": t.created_at,
            "updated_at": t.updated_at,
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
    timeline = await services.timeline_repo.get_timeline(user.tenant_id, patient_id)
    if not timeline:
        raise PatientNotFoundException(patient_id)

    assert_tenant_boundary(user, timeline.tenant_id)

    return {
        "patient_id": timeline.patient_id,
        "tenant_id": timeline.tenant_id,
        "clinic_id": timeline.clinic_id,
        "encounters": [
            {
                "encounter_id": e.encounter_id,
                "encounter_type": e.encounter_type,
                "period_start": e.period_start,
                "period_end": e.period_end,
                "diagnoses": e.diagnoses,
                "observations": [
                    {
                        "observation_id": o.observation_id,
                        "code": o.code,
                        "display_name": o.display_name,
                        "value": o.value,
                        "unit": o.unit,
                        "reference_range_low": o.reference_range_low,
                        "reference_range_high": o.reference_range_high,
                        "is_abnormal": o.is_abnormal,
                    }
                    for o in e.observations
                ],
                "medications": [
                    {
                        "medication_id": m.medication_id,
                        "name": m.name,
                        "rxnorm_code": m.rxnorm_code,
                        "dosage": m.dosage,
                        "status": m.status,
                    }
                    for m in e.medications
                ],
            }
            for e in timeline.encounters
        ],
        "created_at": timeline.created_at,
        "updated_at": timeline.updated_at,
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

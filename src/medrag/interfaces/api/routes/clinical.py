"""Clinical Query, SSE Streaming, and CMO Override API routes."""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
from medrag.application.services.cmo_override import CMOOverrideWorkflow
from medrag.application.services.prompt_composer import ClinicalPromptComposer
from medrag.domain.citation import VerificationStatus, VerifiedClinicalReport
from medrag.domain.exceptions import ClinicalException
from medrag.interfaces.api.dependencies import (
    assert_tenant_boundary,
    get_services,
    require_scope,
)
from medrag.ports.auth import AuthenticatedUser

router = APIRouter(prefix="/api/v1/clinical", tags=["Clinical Query"])

# In-memory query repository for demo/runtime query tracking
_query_store: Dict[str, Dict[str, Any]] = {}


class ClinicalQueryRequest(BaseModel):
    query_text: str = Field(..., min_length=3, description="Clinical question or summary request")
    patient_id: Optional[str] = Field(None, description="Target patient identifier for context enrichment")
    stream: bool = Field(True, description="Whether to stream tokens via Server-Sent Events (SSE)")


class CMOOverrideRequest(BaseModel):
    override_reason: str = Field(..., min_length=10, description="Mandatory clinical justification for unredacting claim")
    cmo_user_id: Optional[str] = Field(None, description="Optional approving CMO user ID")


@router.post("/query")
async def execute_clinical_query(
    req: ClinicalQueryRequest,
    request: Request,
    user: AuthenticatedUser = Depends(require_scope("query:execute")),
):
    """Execute clinical query with hybrid retrieval, deterministic NLI verification, and SSE streaming."""
    services = get_services()
    start_time = time.time()

    # 1. Enforce rate limiting & quotas
    services.rate_limiter.check_and_record_request(user.tenant_id)

    # 2. Retrieve patient context if requested
    patient = None
    if req.patient_id:
        patient = await services.timeline_repo.get_timeline(user.tenant_id, req.patient_id)

    # 3. Retrieve relevant medical literature chunks
    query_vector = await services.embedder.embed_query(req.query_text)
    retrieved_results = await services.vector_store.query_hybrid(
        tenant_id=user.tenant_id,
        query_vector=query_vector,
        query_text=req.query_text,
        top_k=5,
    )
    evidence_chunks = [r.chunk for r in retrieved_results]

    # 4. Compose clinical prompt
    composer = ClinicalPromptComposer()
    prompt = composer.compose_prompt(
        query_text=req.query_text,
        timeline=patient,
        evidence_chunks=evidence_chunks,
    )

    # 5. Generate synthesis text (mock or LLM)
    if evidence_chunks:
        sample_chunk = evidence_chunks[0]
        raw_synthesis = (
            f"Based on clinical documentation, {sample_chunk.text_content} [^1]. "
            "Continuous clinical monitoring is recommended [^1]."
        )
    else:
        raw_synthesis = (
            "Clinical evaluation suggests conservative supportive management based on standard protocol [^1]."
        )

    # 6. Audit & verify claims
    report = await services.claim_auditor.audit_synthesis(
        query_text=req.query_text,
        raw_synthesis=raw_synthesis,
        evidence_chunks=evidence_chunks,
    )

    # Store query record
    query_id = f"qry-{int(time.time() * 1000)}"
    query_record = {
        "query_id": query_id,
        "tenant_id": user.tenant_id,
        "user_id": user.user_id,
        "query_text": req.query_text,
        "patient_id": req.patient_id,
        "report": {
            "query_text": report.query_text,
            "raw_synthesis": report.raw_synthesis,
            "verified_footnotes": [
                {
                    "claim_id": fn.claim.claim_id,
                    "sentence_text": fn.claim.sentence_text,
                    "status": fn.status.value,
                    "entailment_score": fn.entailment_score,
                    "contradiction_score": fn.contradiction_score,
                    "source_document": fn.source_document,
                    "source_page_or_section": fn.source_page_or_section,
                    "supporting_excerpt": fn.supporting_excerpt,
                    "manual_override": fn.manual_override,
                }
                for fn in report.verified_footnotes
            ],
            "redacted_claim_count": report.redacted_claim_count,
            "overall_faithfulness": report.overall_faithfulness,
        },
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _query_store[query_id] = query_record

    # Record audit log
    services.audit_log_repo.record_event(
        event_type="clinical_query.completed",
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        role=user.role,
        resource_type="query",
        resource_id=query_id,
        details={
            "patient_id": req.patient_id,
            "claim_count": len(report.verified_footnotes),
            "redacted_count": report.redacted_claim_count,
            "faithfulness": report.overall_faithfulness,
        },
        trace_id=getattr(request.state, "trace_id", "trace-query"),
    )

    # 7. Non-streaming return
    if not req.stream:
        return query_record

    # 8. SSE Streaming Generator
    async def sse_event_generator():
        services.rate_limiter.acquire_stream(user.tenant_id)
        try:
            # Emit synthesis chunks
            words = report.raw_synthesis.split(" ")
            chunk_size = 4
            for i in range(0, len(words), chunk_size):
                chunk_slice = " ".join(words[i : i + chunk_size]) + " "
                yield {
                    "event": "synthesis_chunk",
                    "data": json.dumps({
                        "chunk_index": i // chunk_size,
                        "text": chunk_slice,
                        "is_final": False,
                    }),
                }
                await asyncio.sleep(0.02)

            # Emit verification footnotes
            for fn in report.verified_footnotes:
                if fn.status == VerificationStatus.CONTRADICTED:
                    yield {
                        "event": "claim_redacted",
                        "data": json.dumps({
                            "claim_id": fn.claim.claim_id,
                            "status": "CONTRADICTED",
                            "score": fn.contradiction_score,
                            "source": fn.source_document,
                        }),
                    }
                else:
                    yield {
                        "event": "citation_verified",
                        "data": json.dumps({
                            "claim_id": fn.claim.claim_id,
                            "status": fn.status.value,
                            "score": fn.entailment_score,
                            "source": fn.source_document,
                        }),
                    }
                await asyncio.sleep(0.01)

            # Emit final completion
            latency_ms = int((time.time() - start_time) * 1000)
            yield {
                "event": "synthesis_complete",
                "data": json.dumps({
                    "query_id": query_id,
                    "total_claims": len(report.verified_footnotes),
                    "verified": sum(1 for fn in report.verified_footnotes if fn.status == VerificationStatus.VERIFIED),
                    "uncertain": sum(1 for fn in report.verified_footnotes if fn.status == VerificationStatus.UNCERTAIN),
                    "redacted": report.redacted_claim_count,
                    "faithfulness": report.overall_faithfulness,
                    "latency_ms": latency_ms,
                }),
            }
        finally:
            services.rate_limiter.release_stream(user.tenant_id)

    return EventSourceResponse(sse_event_generator())


@router.get("/queries")
async def list_queries(
    limit: int = 25,
    user: AuthenticatedUser = Depends(require_scope("query:view_history")),
):
    """List clinical query history for tenant."""
    items = [q for q in _query_store.values() if q["tenant_id"] == user.tenant_id]
    return {"items": items[:limit], "total_count": len(items)}


@router.get("/queries/{query_id}")
async def get_query(
    query_id: str,
    user: AuthenticatedUser = Depends(require_scope("query:view_history")),
):
    """Retrieve verified clinical report by query ID."""
    if query_id not in _query_store:
        raise ClinicalException("QUERY_NOT_FOUND", f"Query '{query_id}' not found", 404)
    record = _query_store[query_id]
    assert_tenant_boundary(user, record["tenant_id"])
    return record


@router.post("/reports/{report_id}/override")
async def cmo_override_claim(
    report_id: str,
    claim_id: str,
    original_text: str,
    req: CMOOverrideRequest,
    request: Request,
    user: AuthenticatedUser = Depends(require_scope("audit:export")),  # cmo or admin
):
    """Chief Medical Officer override to restore redacted clinical claim."""
    services = get_services()
    workflow = CMOOverrideWorkflow()

    # In our store, find matching query/report
    matched_record = None
    for q in _query_store.values():
        if q.get("query_id") == report_id:
            matched_record = q
            break

    if not matched_record:
        raise ClinicalException("REPORT_NOT_FOUND", f"Report '{report_id}' not found", 404)

    assert_tenant_boundary(user, matched_record["tenant_id"])

    # Reconstruct domain report object
    rep_dict = matched_record["report"]
    footnotes = []
    from medrag.domain.citation import ClinicalClaim, VerifiedFootnote
    for idx, f in enumerate(rep_dict["verified_footnotes"]):
        claim = ClinicalClaim(
            claim_id=f["claim_id"],
            sentence_text=f["sentence_text"],
            sentence_index=idx,
            cited_chunk_ids=[],
        )
        status = VerificationStatus(f["status"])
        footnotes.append(
            VerifiedFootnote(
                claim=claim,
                status=status,
                entailment_score=f["entailment_score"],
                contradiction_score=f["contradiction_score"],
                supporting_excerpt=f.get("supporting_excerpt"),
                source_document=f.get("source_document", "Unknown"),
                source_page_or_section=f.get("source_page_or_section", "N/A"),
                manual_override=f.get("manual_override", False),
            )
        )

    domain_report = VerifiedClinicalReport(
        query_text=rep_dict["query_text"],
        raw_synthesis=rep_dict["raw_synthesis"],
        verified_footnotes=footnotes,
        redacted_claim_count=rep_dict["redacted_claim_count"],
        overall_faithfulness=rep_dict["overall_faithfulness"],
    )

    reason = req.override_reason if req.override_reason in CMOOverrideWorkflow.ALLOWED_REASONS else "clinical_judgment"

    overridden_report = workflow.apply_override(
        report=domain_report,
        claim_id=claim_id,
        user_id=req.cmo_user_id or user.user_id,
        reason=reason,
        justification=req.override_reason,
    )

    services.audit_log_repo.record_event(
        event_type="claim.overridden",
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        role=user.role,
        resource_type="claim",
        resource_id=claim_id,
        details={"report_id": report_id, "reason": reason},
        trace_id=getattr(request.state, "trace_id", "trace-override"),
    )

    # Update store
    matched_record["report"]["raw_synthesis"] = overridden_report.raw_synthesis
    matched_record["report"]["redacted_claim_count"] = overridden_report.redacted_claim_count

    return {
        "status": "overridden",
        "report_id": report_id,
        "claim_id": claim_id,
        "raw_synthesis": overridden_report.raw_synthesis,
    }

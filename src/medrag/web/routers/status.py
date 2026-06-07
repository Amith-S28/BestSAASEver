"""Status and health endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from medrag.pipeline import MedRAGPipeline
from medrag.web.deps import get_pipeline
from medrag.web.models import HealthResponse, StatusResponse, DocumentInfo, HereditaryCacheInfo

router = APIRouter(tags=["status"])


@router.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Lightweight liveness check."""
    return HealthResponse()


@router.get("/api/status", response_model=StatusResponse)
async def status(pipeline: MedRAGPipeline = Depends(get_pipeline)) -> StatusResponse:
    """Full pipeline status including LM Studio connection check."""
    info = pipeline.status()
    lmstudio_connected = pipeline.synthesizer.check_connection()
    docs = pipeline.database.list_documents_structured()

    return StatusResponse(
        documents_indexed=info["documents_indexed"],
        documents=[DocumentInfo(**d) for d in docs],
        folders=info.get("folders", 0),
        embedding_model=info["embedding_model"],
        llm_model=info["llm_model"],
        lmstudio_url=info["lmstudio_url"],
        lmstudio_connected=lmstudio_connected,
        db_path=info["db_path"],
        hereditary_cache=HereditaryCacheInfo(**info.get("hereditary_cache", {})),
    )
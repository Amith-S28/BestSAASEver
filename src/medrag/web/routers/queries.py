"""Query endpoint — non-streaming fallback."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Depends

from medrag.pipeline import MedRAGPipeline
from medrag.web.deps import get_pipeline
from medrag.web.models import QueryRequest, QueryResponse

router = APIRouter(tags=["queries"])


@router.post("/api/query", response_model=QueryResponse)
async def query(
    req: QueryRequest,
    pipeline: MedRAGPipeline = Depends(get_pipeline),
) -> QueryResponse:
    """Non-streaming query — returns the full answer at once.

    Supports folder_id scoping and cross_folders hereditary search.
    """
    if not pipeline.synthesizer.check_connection():
        raise HTTPException(
            status_code=503,
            detail="LM Studio is not running. Start it and load a model.",
        )

    try:
        result = await asyncio.to_thread(
            pipeline.query,
            req.question,
            top_k=req.top_k,
            folder_id=req.folder_id,
            cross_folders=req.cross_folders,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")

    return QueryResponse(
        answer=result.answer,
        sources=result.sources,
        model=result.model,
        tokens_used=result.tokens_used,
    )
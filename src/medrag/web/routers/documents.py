"""Document management endpoints — list, upload, delete."""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query

from medrag.config import settings
from medrag.pipeline import MedRAGPipeline
from medrag.web.deps import get_pipeline
from medrag.web.models import (
    DeleteResponse,
    DocumentInfo,
    DocumentListResponse,
    UploadResponse,
)

router = APIRouter(tags=["documents"])


@router.get("/api/documents", response_model=DocumentListResponse)
async def list_documents(
    folder_id: str | None = Query(default=None, description="Filter by folder"),
    pipeline: MedRAGPipeline = Depends(get_pipeline),
) -> DocumentListResponse:
    """List indexed documents, optionally filtered by folder."""
    docs = pipeline.database.list_documents_structured(folder_id=folder_id)
    return DocumentListResponse(
        total=len(docs),
        documents=[DocumentInfo(**d) for d in docs],
    )


@router.post("/api/documents/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    folder_id: str = Form(default="default"),
    pipeline: MedRAGPipeline = Depends(get_pipeline),
) -> UploadResponse:
    """Upload and ingest a single file (PDF or image) into a folder."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Accepted: PDF, JPG, PNG, TIFF, BMP, WebP",
        )

    raw_path = Path(settings.raw_dir) / (file.filename or "upload")
    raw_path.parent.mkdir(parents=True, exist_ok=True)

    with open(raw_path, "wb") as f:
        content = await file.read()
        if len(content) > settings.max_upload_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Max: {settings.max_upload_size_mb}MB",
            )
        f.write(content)

    try:
        doc = await asyncio.to_thread(pipeline.ingest_file, str(raw_path), folder_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")

    return UploadResponse(
        doc_id=doc.doc_id,
        folder_id=folder_id,
        filename=doc.filename,
        pages=doc.pages,
        engine=doc.metadata.get("engine", "unknown"),
    )


@router.delete("/api/documents/{doc_id}", response_model=DeleteResponse)
async def delete_document(
    doc_id: str,
    pipeline: MedRAGPipeline = Depends(get_pipeline),
) -> DeleteResponse:
    """Remove a document from the index."""
    deleted = pipeline.database.delete_document(doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
    return DeleteResponse(deleted=True, doc_id=doc_id)
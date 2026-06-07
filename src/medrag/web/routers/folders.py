"""Folder (family member) management endpoints — CRUD."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends

from medrag.pipeline import MedRAGPipeline
from medrag.web.deps import get_pipeline
from medrag.web.models import (
    FolderCreate,
    FolderUpdate,
    FolderInfoResponse,
    FolderListResponse,
    FolderDeleteResponse,
)

router = APIRouter(tags=["folders"])


@router.get("/api/folders", response_model=FolderListResponse)
async def list_folders(
    pipeline: MedRAGPipeline = Depends(get_pipeline),
) -> FolderListResponse:
    """List all family member folders with document counts."""
    folders = pipeline.list_folders()
    return FolderListResponse(
        folders=[
            FolderInfoResponse(
                folder_id=f.folder_id,
                name=f.name,
                relationship=f.relationship,
                notes=f.notes,
                created_at=f.created_at,
                document_count=f.document_count,
            )
            for f in folders
        ]
    )


@router.post("/api/folders", response_model=FolderInfoResponse, status_code=201)
async def create_folder(
    req: FolderCreate,
    pipeline: MedRAGPipeline = Depends(get_pipeline),
) -> FolderInfoResponse:
    """Create a new family member folder."""
    folder = pipeline.create_folder(
        name=req.name,
        relationship=req.relationship,
        notes=req.notes,
    )
    return FolderInfoResponse(
        folder_id=folder.folder_id,
        name=folder.name,
        relationship=folder.relationship,
        notes=folder.notes,
        created_at=folder.created_at,
        document_count=folder.document_count,
    )


@router.patch("/api/folders/{folder_id}", response_model=FolderInfoResponse)
async def update_folder(
    folder_id: str,
    req: FolderUpdate,
    pipeline: MedRAGPipeline = Depends(get_pipeline),
) -> FolderInfoResponse:
    """Update folder name or notes."""
    folder = pipeline.update_folder(
        folder_id=folder_id,
        name=req.name,
        notes=req.notes,
    )
    if not folder:
        raise HTTPException(status_code=404, detail=f"Folder {folder_id} not found")
    return FolderInfoResponse(
        folder_id=folder.folder_id,
        name=folder.name,
        relationship=folder.relationship,
        notes=folder.notes,
        created_at=folder.created_at,
        document_count=folder.document_count,
    )


@router.delete("/api/folders/{folder_id}", response_model=FolderDeleteResponse)
async def delete_folder(
    folder_id: str,
    pipeline: MedRAGPipeline = Depends(get_pipeline),
) -> FolderDeleteResponse:
    """Delete a folder and all its documents + conversations."""
    # Count before deletion for response
    doc_count = pipeline.database.count(folder_id=folder_id)
    conv_count = len(pipeline.list_conversations(folder_id))

    deleted = pipeline.delete_folder(folder_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Folder {folder_id} not found")

    return FolderDeleteResponse(
        deleted=True,
        folder_id=folder_id,
        documents_removed=doc_count,
        conversations_removed=conv_count,
    )
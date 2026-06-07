"""Conversation history endpoints — create, list, load, delete."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends

from medrag.pipeline import MedRAGPipeline
from medrag.web.deps import get_pipeline
from medrag.web.models import (
    ConversationInfo,
    ConversationListResponse,
    ConversationDetail,
    ChatMessageResponse,
    ConversationDeleteResponse,
    ConversationCreateResponse,
)

router = APIRouter(tags=["conversations"])


@router.post("/api/folders/{folder_id}/conversations", response_model=ConversationCreateResponse, status_code=201)
async def create_conversation(
    folder_id: str,
    pipeline: MedRAGPipeline = Depends(get_pipeline),
) -> ConversationCreateResponse:
    """Start a new conversation in a folder."""
    conv = pipeline.create_conversation(folder_id)
    return ConversationCreateResponse(
        conv_id=conv.conv_id,
        folder_id=conv.folder_id,
        title=conv.title,
    )


@router.get("/api/folders/{folder_id}/conversations", response_model=ConversationListResponse)
async def list_conversations(
    folder_id: str,
    pipeline: MedRAGPipeline = Depends(get_pipeline),
) -> ConversationListResponse:
    """List all conversations for a folder."""
    convs = pipeline.list_conversations(folder_id)
    return ConversationListResponse(
        conversations=[
            ConversationInfo(
                conv_id=c["conv_id"],
                folder_id=c["folder_id"],
                title=c["title"],
                message_count=c["message_count"],
                created_at=c["created_at"],
                updated_at=c["updated_at"],
            )
            for c in convs
        ]
    )


@router.get("/api/conversations/{folder_id}/{conv_id}", response_model=ConversationDetail)
async def get_conversation(
    folder_id: str,
    conv_id: str,
    pipeline: MedRAGPipeline = Depends(get_pipeline),
) -> ConversationDetail:
    """Load a full conversation with all messages."""
    conv = pipeline.load_conversation(folder_id, conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail=f"Conversation {conv_id} not found")
    return ConversationDetail(
        conv_id=conv.conv_id,
        folder_id=conv.folder_id,
        title=conv.title,
        messages=[
            ChatMessageResponse(role=m.role, content=m.content, sources=m.sources)
            for m in conv.messages
        ],
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


@router.delete("/api/conversations/{folder_id}/{conv_id}", response_model=ConversationDeleteResponse)
async def delete_conversation(
    folder_id: str,
    conv_id: str,
    pipeline: MedRAGPipeline = Depends(get_pipeline),
) -> ConversationDeleteResponse:
    """Delete a conversation."""
    deleted = pipeline.delete_conversation(folder_id, conv_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Conversation {conv_id} not found")
    return ConversationDeleteResponse(deleted=True, conv_id=conv_id)
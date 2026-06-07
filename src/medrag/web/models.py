"""Pydantic v2 request/response schemas for the web API."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Requests ────────────────────────────────────────────────────────────────


class QueryRequest(BaseModel):
    """User query against the document store."""

    question: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    folder_id: str | None = Field(default=None, description="Scope search to this folder")
    cross_folders: bool = Field(default=False, description="Search all folders for hereditary patterns")


class FolderCreate(BaseModel):
    """Create a new family member folder."""

    name: str = Field(..., min_length=1, max_length=100)
    relationship: str = Field(default="self", description="self, mother, father, sibling, spouse, child, other")
    notes: str = Field(default="")


class FolderUpdate(BaseModel):
    """Update folder metadata."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    notes: str | None = Field(default=None)


# ── Responses ───────────────────────────────────────────────────────────────


class HereditaryCacheInfo(BaseModel):
    """Status of the hereditary conditions cache."""

    cache_exists: bool
    last_sync: str | None
    total_conditions: int


class StatusResponse(BaseModel):
    """Pipeline status."""

    documents_indexed: int
    documents: list[DocumentInfo]
    folders: int
    embedding_model: str
    llm_model: str
    lmstudio_url: str
    lmstudio_connected: bool
    db_path: str
    hereditary_cache: HereditaryCacheInfo = Field(
        default_factory=lambda: HereditaryCacheInfo(
            cache_exists=False, last_sync=None, total_conditions=0,
        )
    )


class DocumentInfo(BaseModel):
    """Summary of an indexed document."""

    doc_id: str
    folder_id: str = "default"
    filename: str
    pages: int
    engine: str


class DocumentListResponse(BaseModel):
    """List of indexed documents."""

    total: int
    documents: list[DocumentInfo]


class QueryResponse(BaseModel):
    """Non-streaming query response."""

    answer: str
    sources: list[str]
    model: str
    tokens_used: int


class UploadResponse(BaseModel):
    """Result of file upload + ingestion."""

    doc_id: str
    folder_id: str = "default"
    filename: str
    pages: int
    engine: str


class HealthResponse(BaseModel):
    """Liveness check."""

    status: str = "ok"


class DeleteResponse(BaseModel):
    """Document deletion result."""

    deleted: bool
    doc_id: str


# ── Folder Responses ──────────────────────────────────────────────────────


class FolderInfoResponse(BaseModel):
    """A single folder (family member)."""

    folder_id: str
    name: str
    relationship: str
    notes: str
    created_at: str
    document_count: int = 0


class FolderListResponse(BaseModel):
    """List of all folders."""

    folders: list[FolderInfoResponse]


class FolderDeleteResponse(BaseModel):
    """Result of folder deletion."""

    deleted: bool
    folder_id: str
    documents_removed: int
    conversations_removed: int


# ── Conversation Responses ────────────────────────────────────────────────


class ConversationInfo(BaseModel):
    """Summary of a conversation."""

    conv_id: str
    folder_id: str
    title: str
    message_count: int
    created_at: str
    updated_at: str


class ConversationListResponse(BaseModel):
    """List of conversations for a folder."""

    conversations: list[ConversationInfo]


class ChatMessageResponse(BaseModel):
    """A single message in a conversation."""

    role: str
    content: str
    sources: list[str] = []


class ConversationDetail(BaseModel):
    """Full conversation with all messages."""

    conv_id: str
    folder_id: str
    title: str
    messages: list[ChatMessageResponse]
    created_at: str
    updated_at: str


class ConversationDeleteResponse(BaseModel):
    """Result of conversation deletion."""

    deleted: bool
    conv_id: str


class ConversationCreateResponse(BaseModel):
    """Result of conversation creation."""

    conv_id: str
    folder_id: str
    title: str
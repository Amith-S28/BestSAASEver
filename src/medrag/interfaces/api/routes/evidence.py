"""Evidence and Medical Literature retrieval API routes."""

from fastapi import APIRouter, Depends
from medrag.domain.exceptions import ChunkNotFoundException
from medrag.interfaces.api.dependencies import get_services, require_scope
from medrag.ports.auth import AuthenticatedUser

router = APIRouter(prefix="/api/v1/evidence", tags=["Evidence Literature"])


@router.get("/{chunk_id}")
async def get_evidence_chunk(
    chunk_id: str,
    user: AuthenticatedUser = Depends(require_scope("evidence:view")),
):
    """Retrieve full text and metadata for a specific cited evidence chunk."""
    services = get_services()
    chunk = await services.vector_store.get_chunk_by_id(user.tenant_id, chunk_id)
    if not chunk:
        raise ChunkNotFoundException(chunk_id)

    return {
        "chunk_id": chunk.chunk_id,
        "document_id": chunk.document_id,
        "title": chunk.title,
        "chapter": chunk.chapter,
        "page_number": chunk.page_number,
        "text_content": chunk.text_content,
        "specialty": chunk.specialty,
        "snomed_codes": chunk.snomed_codes,
        "rxnorm_codes": chunk.rxnorm_codes,
        "loinc_codes": chunk.loinc_codes,
        "corpus_license_tier": chunk.corpus_license_tier,
    }

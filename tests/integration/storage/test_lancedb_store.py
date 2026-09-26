"""Integration tests for LanceDB hybrid vector store adapter."""

from datetime import datetime, timezone
import pytest
import shutil

from medrag.domain.exceptions import TenantIsolationViolationException
from medrag.domain.literature import MedicalChunk
from medrag.infrastructure.models.embedder import DeterministicEmbedder
from medrag.infrastructure.storage.lancedb_store import LanceDBVectorStore


@pytest.fixture
def temp_lancedb_store(tmp_path):
    """Fixture providing an isolated LanceDB store in a temporary directory."""
    db_dir = str(tmp_path / "lancedb_test")
    store = LanceDBVectorStore(db_uri=db_dir, embedding_dim=128)
    yield store
    shutil.rmtree(db_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_insert_and_count_chunks(temp_lancedb_store):
    """Store batch inserts chunks and tracks counts."""
    embedder = DeterministicEmbedder(dim=128)
    chunks = [
        MedicalChunk(
            chunk_id="chk-001",
            document_id="doc-harrisons",
            title="Harrison's Internal Medicine",
            chapter="Nephrology",
            page_number=100,
            text_content="Acute kidney injury is characterized by rapid decline in GFR.",
            specialty="Nephrology",
            snomed_codes=["14669001"],
            corpus_license_tier="tier1_open",
        ),
        MedicalChunk(
            chunk_id="chk-002",
            document_id="doc-harrisons",
            title="Harrison's Internal Medicine",
            chapter="Cardiology",
            page_number=200,
            text_content="Heart failure with reduced ejection fraction requires guideline therapy.",
            specialty="Cardiology",
            snomed_codes=["84114007"],
            corpus_license_tier="tier1_open",
        ),
    ]
    vectors = await embedder.embed_batch([c.text_content for c in chunks])

    # Insert into system tier
    inserted = await temp_lancedb_store.insert_chunks_with_vectors("system", chunks, vectors)
    assert inserted == 2

    count = await temp_lancedb_store.count_chunks("tenant-hospital-a")
    assert count == 2


@pytest.mark.asyncio
async def test_tenant_isolation_boundary(temp_lancedb_store):
    """Store strictly isolates tenant-specific literature from other tenants."""
    embedder = DeterministicEmbedder(dim=128)

    chunk_a = MedicalChunk(
        chunk_id="chk-priv-a",
        document_id="doc-priv-a",
        title="Hospital A Guideline",
        chapter="Protocol",
        page_number=1,
        text_content="Hospital A specific antibiotic stewardship protocol.",
        specialty="Infectious Disease",
        corpus_license_tier="tier3_institutional",
    )
    chunk_b = MedicalChunk(
        chunk_id="chk-priv-b",
        document_id="doc-priv-b",
        title="Hospital B Guideline",
        chapter="Protocol",
        page_number=1,
        text_content="Hospital B specific chemotherapy formulary.",
        specialty="Oncology",
        corpus_license_tier="tier3_institutional",
    )

    vec_a = await embedder.embed_passage(chunk_a.text_content)
    vec_b = await embedder.embed_passage(chunk_b.text_content)

    await temp_lancedb_store.insert_chunks_with_vectors("tenant-a", [chunk_a], [vec_a])
    await temp_lancedb_store.insert_chunks_with_vectors("tenant-b", [chunk_b], [vec_b])

    # Tenant A queries: must find only chunk_a, NEVER chunk_b
    q_vec = await embedder.embed_query("antibiotic protocol")
    results_a = await temp_lancedb_store.query_hybrid(
        tenant_id="tenant-a",
        query_vector=q_vec,
        query_text="antibiotic protocol",
        top_k=5,
    )
    result_ids_a = [e.chunk.chunk_id for e in results_a]
    assert "chk-priv-a" in result_ids_a
    assert "chk-priv-b" not in result_ids_a

    # Empty tenant context raises exception
    with pytest.raises(TenantIsolationViolationException):
        await temp_lancedb_store.query_hybrid("", q_vec, "test")


@pytest.mark.asyncio
async def test_hybrid_retrieval_and_rrf_scoring(temp_lancedb_store):
    """Hybrid search merges vector cosine and BM25 rankings via RRF."""
    embedder = DeterministicEmbedder(dim=128)
    chunk = MedicalChunk(
        chunk_id="chk-neph-1",
        document_id="doc-neph",
        title="Renal Physiology",
        chapter="Glomerulus",
        page_number=45,
        text_content="Creatinine clearance rate measurement in clinical nephrology.",
        specialty="Nephrology",
        snomed_codes=["14669001"],
    )
    vec = await embedder.embed_passage(chunk.text_content)
    await temp_lancedb_store.insert_chunks_with_vectors("system", [chunk], [vec])

    q_vec = await embedder.embed_query("creatinine clearance")
    evidence = await temp_lancedb_store.query_hybrid(
        tenant_id="tenant-mayo",
        query_vector=q_vec,
        query_text="creatinine clearance",
        top_k=1,
    )
    assert len(evidence) == 1
    assert evidence[0].chunk.chunk_id == "chk-neph-1"
    assert evidence[0].rrf_score > 0.0

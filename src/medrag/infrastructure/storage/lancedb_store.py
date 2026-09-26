"""LanceDB Arrow vector store adapter implementing medrag.ports.storage.IVectorStore."""

from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import pyarrow as pa
import lancedb

from medrag.domain.exceptions import TenantIsolationViolationException
from medrag.domain.literature import MedicalChunk, RetrievedEvidence
from medrag.infrastructure.retrieval.rrf import compute_rrf_scores


def get_literature_arrow_schema(dim: int = 1024) -> pa.Schema:
    """Canonical Apache Arrow schema for clinical_literature table."""
    return pa.schema([
        pa.field("chunk_id", pa.string(), nullable=False),
        pa.field("tenant_id", pa.string(), nullable=False),
        pa.field("corpus_license_tier", pa.string(), nullable=False),
        pa.field("document_id", pa.string(), nullable=False),
        pa.field("title", pa.string(), nullable=False),
        pa.field("chapter", pa.string(), nullable=False),
        pa.field("page_number", pa.int32(), nullable=False),
        pa.field("text_content", pa.string(), nullable=False),
        pa.field("vector", pa.list_(pa.float32(), dim), nullable=False),
        pa.field("snomed_codes", pa.list_(pa.string()), nullable=False),
        pa.field("rxnorm_codes", pa.list_(pa.string()), nullable=False),
        pa.field("loinc_codes", pa.list_(pa.string()), nullable=False),
        pa.field("specialty", pa.string(), nullable=False),
        pa.field("ingested_at", pa.timestamp("us"), nullable=False),
    ])


class LanceDBVectorStore:
    """Embedded LanceDB vector database adapter with hybrid search and RRF fusion."""

    def __init__(
        self,
        db_uri: str = "./data/lancedb",
        table_name: str = "clinical_literature",
        embedding_dim: int = 1024,
    ) -> None:
        self.db_uri = db_uri
        self.table_name = table_name
        self.embedding_dim = embedding_dim
        Path(self.db_uri).mkdir(parents=True, exist_ok=True)
        self.db = lancedb.connect(self.db_uri)
        self._ensure_table()

    def _table_exists(self) -> bool:
        """Check if table exists using list_tables."""
        try:
            res = self.db.list_tables()
            table_list = getattr(res, "tables", res)
            return self.table_name in table_list
        except Exception:
            return self.table_name in self.db.table_names()

    def _ensure_table(self) -> None:
        """Create table with canonical schema if not already present."""
        if not self._table_exists():
            schema = get_literature_arrow_schema(self.embedding_dim)
            self.table = self.db.create_table(self.table_name, schema=schema)
        else:
            self.table = self.db.open_table(self.table_name)

    async def insert_chunks(self, tenant_id: str, chunks: List[MedicalChunk]) -> int:
        """Batch insert chunks with metadata and tenant scoping."""
        if not tenant_id or not tenant_id.strip():
            raise TenantIsolationViolationException("Empty tenant context for chunk insertion")

        if not chunks:
            return 0

        rows: List[Dict[str, Any]] = []
        now = datetime.now(timezone.utc)

        for chunk in chunks:
            rows.append({
                "chunk_id": chunk.chunk_id,
                "tenant_id": tenant_id,
                "corpus_license_tier": chunk.corpus_license_tier,
                "document_id": chunk.document_id,
                "title": chunk.title,
                "chapter": chunk.chapter,
                "page_number": chunk.page_number,
                "text_content": chunk.text_content,
                "vector": [0.0] * self.embedding_dim,  # Placeholder or supplied vector
                "snomed_codes": chunk.snomed_codes or [],
                "rxnorm_codes": chunk.rxnorm_codes or [],
                "loinc_codes": chunk.loinc_codes or [],
                "specialty": chunk.specialty,
                "ingested_at": chunk.ingested_at or now,
            })

        self.table.add(rows)
        return len(rows)

    async def insert_chunks_with_vectors(
        self, tenant_id: str, chunks: List[MedicalChunk], vectors: List[List[float]]
    ) -> int:
        """Insert chunks alongside dense embedding vectors."""
        if not tenant_id or not tenant_id.strip():
            raise TenantIsolationViolationException("Empty tenant context for chunk insertion")

        if not chunks:
            return 0

        if len(chunks) != len(vectors):
            raise ValueError("Chunk count must match vector count")

        rows: List[Dict[str, Any]] = []
        now = datetime.now(timezone.utc)

        for chunk, vec in zip(chunks, vectors):
            rows.append({
                "chunk_id": chunk.chunk_id,
                "tenant_id": tenant_id,
                "corpus_license_tier": chunk.corpus_license_tier,
                "document_id": chunk.document_id,
                "title": chunk.title,
                "chapter": chunk.chapter,
                "page_number": chunk.page_number,
                "text_content": chunk.text_content,
                "vector": vec,
                "snomed_codes": chunk.snomed_codes or [],
                "rxnorm_codes": chunk.rxnorm_codes or [],
                "loinc_codes": chunk.loinc_codes or [],
                "specialty": chunk.specialty,
                "ingested_at": chunk.ingested_at or now,
            })

        self.table.add(rows)
        return len(rows)

    async def query_hybrid(
        self,
        tenant_id: str,
        query_vector: List[float],
        query_text: str,
        snomed_filters: Optional[List[str]] = None,
        rxnorm_filters: Optional[List[str]] = None,
        top_k: int = 25,
    ) -> List[RetrievedEvidence]:
        """Hybrid dense vector + lexical search fused via Reciprocal Rank Fusion (RRF)."""
        if not tenant_id or not tenant_id.strip():
            raise TenantIsolationViolationException("Empty tenant context for hybrid search")

        # Mandatory tenant predicate: tenant data + shared system data
        tenant_predicate = f"(tenant_id = '{tenant_id}' OR tenant_id = 'system')"

        # Check if table has data
        try:
            total_rows = self.table.count_rows(tenant_predicate)
        except Exception:
            total_rows = 0

        if total_rows == 0:
            return []

        # 1. Dense vector search
        search_builder = self.table.search(query_vector).where(tenant_predicate)
        dense_results = search_builder.limit(top_k * 2).to_list()
        dense_chunk_ids = [r["chunk_id"] for r in dense_results]

        # 2. Sparse / lexical ranking (token overlap matching over candidate partition)
        query_terms = set(query_text.lower().split())
        sparse_candidates = []
        chunk_map: Dict[str, Dict[str, Any]] = {}

        for row in dense_results:
            cid = row["chunk_id"]
            chunk_map[cid] = row
            text = row["text_content"].lower()
            overlap_score = sum(text.count(term) for term in query_terms)
            sparse_candidates.append((cid, overlap_score))

        sparse_candidates.sort(key=lambda item: item[1], reverse=True)
        sparse_chunk_ids = [cid for cid, _ in sparse_candidates]

        # 3. Reciprocal Rank Fusion
        rrf_rankings = compute_rrf_scores(dense_chunk_ids, sparse_chunk_ids, k=60)

        # 4. Construct domain RetrievedEvidence
        evidence_list: List[RetrievedEvidence] = []
        for chunk_id, rrf_score in rrf_rankings[:top_k]:
            row = chunk_map[chunk_id]

            # Apply ontology filtering if specified
            if snomed_filters and not any(sc in row.get("snomed_codes", []) for sc in snomed_filters):
                continue
            if rxnorm_filters and not any(rc in row.get("rxnorm_codes", []) for rc in rxnorm_filters):
                continue

            chunk = MedicalChunk(
                chunk_id=row["chunk_id"],
                document_id=row["document_id"],
                title=row["title"],
                chapter=row["chapter"],
                page_number=row["page_number"],
                text_content=row["text_content"],
                specialty=row["specialty"],
                snomed_codes=list(row.get("snomed_codes", [])),
                rxnorm_codes=list(row.get("rxnorm_codes", [])),
                loinc_codes=list(row.get("loinc_codes", [])),
                ingested_at=row.get("ingested_at"),
                corpus_license_tier=row.get("corpus_license_tier", "tier1_open"),
            )
            dense_score = float(1.0 - (row.get("_distance", 0.0) or 0.0))
            evidence_list.append(
                RetrievedEvidence(
                    chunk=chunk,
                    vector_score=dense_score,
                    bm25_score=float(len(query_terms)),
                    rrf_score=float(rrf_score),
                    reranker_score=None,
                )
            )

        return evidence_list

    async def delete_by_tenant(self, tenant_id: str) -> int:
        """Purge all vector entries belonging to a tenant."""
        if not tenant_id or not tenant_id.strip() or tenant_id == "system":
            raise TenantIsolationViolationException("Cannot delete system corpus or empty tenant")

        count_before = self.table.count_rows(f"tenant_id = '{tenant_id}'")
        self.table.delete(f"tenant_id = '{tenant_id}'")
        return count_before

    async def count_chunks(self, tenant_id: str) -> int:
        """Count total chunks accessible to a tenant."""
        if not tenant_id or not tenant_id.strip():
            raise TenantIsolationViolationException("Empty tenant context for count")

        predicate = f"tenant_id = '{tenant_id}' OR tenant_id = 'system'"
        return self.table.count_rows(predicate)

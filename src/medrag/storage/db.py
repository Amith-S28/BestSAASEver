"""LanceDB storage — persistent vector + full-text search with RRF.

Architecture: LanceDB is an embedded, serverless database (like SQLite for vectors).
  • Zero idle memory (disk-backed Apache Arrow)
  • IVF-PQ index for semantic search
  • Tantivy FTS index for exact keyword/alphanumeric matching
  • Reciprocal Rank Fusion (RRF) merges both result sets
  • Folder-scoped search — filter by patient/family member

Documents are stored WHOLE — no chunking. Each row = one complete medical document.
Each document belongs to a folder (patient profile).
"""

from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass

import lancedb
import numpy as np
import pyarrow as pa
from lancedb.pydantic import LanceModel, Vector

from medrag.config import settings
from medrag.ingestion.parser import ParsedDocument


# ── Schema ─────────────────────────────────────────────────────────────────


class DocumentRecord(LanceModel):
    """A single medical document stored in LanceDB."""

    doc_id: str
    folder_id: str  # which patient/family member this belongs to
    filename: str
    markdown: str
    pages: int
    metadata_json: str  # serialized metadata dict
    vector: Vector(settings.embedding_dim)  # type: ignore[valid-type]


@dataclass
class SearchResult:
    """A single search result from hybrid query."""

    doc_id: str
    folder_id: str
    filename: str
    markdown: str
    score: float
    metadata: dict


# ── Database ──────────────────────────────────────────────────────────────


class MedRAGDatabase:
    """Embedded vector database for medical documents."""

    TABLE_NAME = "documents"

    def __init__(self, db_dir: str | None = None):
        self.db_dir = Path(db_dir or settings.lancedb_dir)
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self._db: lancedb.DBConnection | None = None

    @property
    def db(self) -> lancedb.DBConnection:
        """Lazy database connection."""
        if self._db is None:
            self._db = lancedb.connect(str(self.db_dir))
        return self._db

    def _get_table(self) -> lancedb.table.Table | None:
        """Get the documents table if it exists."""
        if self.TABLE_NAME in self.db.table_names():
            return self.db.open_table(self.TABLE_NAME)
        return None

    def _ensure_schema(self) -> None:
        """Migrate old table schema to include folder_id if missing."""
        if self.TABLE_NAME not in self.db.table_names():
            return
        table = self.db.open_table(self.TABLE_NAME)
        schema = table.schema
        col_names = [f.name for f in schema]

        if "folder_id" not in col_names:
            # Old schema without folder_id — need to rebuild
            print("[medrag] Migrating database schema to add folder_id...")
            df = table.to_pandas()
            # Drop old table
            self.db.drop_table(self.TABLE_NAME)
            # Add folder_id column with "default" value
            df["folder_id"] = "default"
            # Re-create table
            new_table = self.db.create_table(self.TABLE_NAME, df)
            self._create_vector_index(new_table)
            self._create_fts_index(new_table)
            print(f"[medrag] Migration complete — {len(df)} documents now have folder_id")

    def index_documents(
        self,
        documents: list[ParsedDocument],
        vectors: np.ndarray,
        folder_id: str = "default",
    ) -> int:
        """Store parsed documents with their embedding vectors.

        Args:
            documents: Parsed medical documents.
            vectors: Corresponding embedding vectors (len(docs), dim).
            folder_id: Which patient folder these documents belong to.

        Returns:
            Number of documents indexed.
        """
        self._ensure_schema()

        if len(documents) != len(vectors):
            raise ValueError(
                f"Mismatch: {len(documents)} documents vs {len(vectors)} vectors"
            )

        records = []
        for doc, vec in zip(documents, vectors):
            records.append(
                DocumentRecord(
                    doc_id=doc.doc_id,
                    folder_id=folder_id,
                    filename=doc.filename,
                    markdown=doc.markdown,
                    pages=doc.pages,
                    metadata_json=json.dumps(doc.metadata),
                    vector=vec.tolist(),
                )
            )

        # Create or append to table
        if self.TABLE_NAME not in self.db.table_names():
            table = self.db.create_table(self.TABLE_NAME, records)
            print(f"[medrag] Created table '{self.TABLE_NAME}' with {len(records)} documents in folder '{folder_id}'")
        else:
            table = self.db.open_table(self.TABLE_NAME)
            table.add(records)
            print(f"[medrag] Added {len(records)} documents to folder '{folder_id}'")

        # Build vector index for semantic search
        self._create_vector_index(table)
        # Build full-text index for keyword search
        self._create_fts_index(table)

        return len(records)

    def _create_vector_index(self, table: lancedb.table.Table) -> None:
        """Create IVF-PQ index for fast vector similarity search."""
        try:
            row_count = table.count_rows()
            # IVF-PQ needs at least 256 rows; scale partitions to data size
            if row_count < 256:
                print(f"[medrag] Vector index deferred — need 256+ rows (have {row_count})")
                return
            num_partitions = min(32, max(1, row_count // 8))
            table.create_index(
                vector_column_name="vector",
                index_type="IVF_PQ",
                num_partitions=num_partitions,
                num_sub_vectors=64,
                replace=True,
            )
            print(f"[medrag] Vector index (IVF-PQ) created — {num_partitions} partitions")
        except Exception as e:
            print(f"[medrag] Vector index creation skipped: {e}")

    def _create_fts_index(self, table: lancedb.table.Table) -> None:
        """Create full-text search index for exact keyword matching."""
        try:
            table.create_fts_index("markdown", replace=True)
            print("[medrag] Full-text search index created")
        except Exception as e:
            print(f"[medrag] FTS index creation skipped: {e}")

    def search(
        self,
        query_vector: np.ndarray,
        query_text: str,
        limit: int = 5,
        folder_id: str | None = None,
    ) -> list[SearchResult]:
        """Hybrid search combining vector similarity + keyword matching.

        Uses Reciprocal Rank Fusion (RRF) to merge both result sets.

        Args:
            query_vector: Embedded query vector (dim,).
            query_text: Original query text for FTS.
            limit: Max results to return.
            folder_id: If set, only search documents in this folder.
                       If None, search ALL folders (for hereditary/cross-family search).

        Returns:
            Ranked search results.
        """
        self._ensure_schema()
        table = self._get_table()
        if table is None:
            print("[medrag] No documents indexed yet")
            return []

        # Build filter clause for folder scoping
        filter_clause = f'folder_id = "{folder_id}"' if folder_id else None

        # Vector search
        vector_query = table.search(query_vector.tolist()).limit(limit * 2)
        if filter_clause:
            vector_query = vector_query.where(filter_clause)
        vector_results = vector_query.to_pydantic(DocumentRecord)

        # Full-text search
        fts_results = []
        try:
            fts_query = table.search(query_text, query_type="fts").limit(limit * 2)
            if filter_clause:
                fts_query = fts_query.where(filter_clause)
            fts_results = fts_query.to_pydantic(DocumentRecord)
        except Exception:
            fts_results = []

        # Reciprocal Rank Fusion
        return self._rrf_merge(vector_results, fts_results, limit)

    def _rrf_merge(
        self,
        vector_results: list[DocumentRecord],
        fts_results: list[DocumentRecord],
        limit: int,
        k: int = 60,
    ) -> list[SearchResult]:
        """Merge results using Reciprocal Rank Fusion.

        RRF formula: score(d) = sum(1 / (k + rank_i)) for each ranked list i
        """
        scores: dict[str, float] = {}
        doc_map: dict[str, DocumentRecord] = {}

        for rank, doc in enumerate(vector_results, 1):
            scores[doc.doc_id] = scores.get(doc.doc_id, 0) + 1.0 / (k + rank)
            doc_map[doc.doc_id] = doc

        for rank, doc in enumerate(fts_results, 1):
            scores[doc.doc_id] = scores.get(doc.doc_id, 0) + 1.0 / (k + rank)
            doc_map[doc.doc_id] = doc

        # Sort by fused score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]

        return [
            SearchResult(
                doc_id=doc_id,
                folder_id=doc_map[doc_id].folder_id,
                filename=doc_map[doc_id].filename,
                markdown=doc_map[doc_id].markdown,
                score=score,
                metadata=json.loads(doc_map[doc_id].metadata_json),
            )
            for doc_id, score in ranked
        ]

    def count(self, folder_id: str | None = None) -> int:
        """Return number of indexed documents, optionally filtered by folder."""
        self._ensure_schema()
        table = self._get_table()
        if table is None:
            return 0
        df = table.to_pandas()
        if folder_id:
            df = df[df["folder_id"] == folder_id]
        return len(df)

    def list_documents(self) -> list[str]:
        """List all indexed document IDs."""
        table = self._get_table()
        if table is None:
            return []
        df = table.to_pandas(columns=["doc_id", "filename", "pages"])
        return [f"{row.doc_id} | {row.filename} ({row.pages}p)" for _, row in df.iterrows()]

    def list_documents_structured(self, folder_id: str | None = None) -> list[dict]:
        """List indexed documents as structured dicts, optionally filtered by folder."""
        self._ensure_schema()
        table = self._get_table()
        if table is None:
            return []
        df = table.to_pandas(columns=["doc_id", "folder_id", "filename", "pages", "metadata_json"])
        if folder_id:
            df = df[df["folder_id"] == folder_id]
        results = []
        for _, row in df.iterrows():
            meta = {}
            try:
                meta = json.loads(row.metadata_json)
            except (json.JSONDecodeError, TypeError):
                pass
            results.append({
                "doc_id": row.doc_id,
                "folder_id": row.folder_id,
                "filename": row.filename,
                "pages": row.pages,
                "engine": meta.get("engine", "unknown"),
            })
        return results

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document from the index by doc_id."""
        table = self._get_table()
        if table is None:
            return False
        try:
            table.delete(f'doc_id = "{doc_id}"')
            return True
        except Exception:
            return False

    def delete_folder_documents(self, folder_id: str) -> int:
        """Delete all documents belonging to a folder. Returns count deleted."""
        table = self._get_table()
        if table is None:
            return 0
        try:
            df = table.to_pandas(columns=["doc_id"])
            df_filtered = df if folder_id is None else table.to_pandas()
            count = 0
            # Get doc IDs for this folder
            all_df = table.to_pandas(columns=["doc_id", "folder_id"])
            folder_docs = all_df[all_df["folder_id"] == folder_id]
            for _, row in folder_docs.iterrows():
                table.delete(f'doc_id = "{row.doc_id}"')
                count += 1
            return count
        except Exception:
            return 0
"""Folder (patient profile) storage — LanceDB table for family member management.

Each folder represents a person whose medical documents are tracked.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path

import lancedb
from lancedb.pydantic import LanceModel

from medrag.config import settings


class FolderRecord(LanceModel):
    """A patient/family member folder."""

    folder_id: str
    name: str
    relationship: str  # self, mother, father, sibling, spouse, child, other
    notes: str = ""
    created_at: str


@dataclass
class FolderInfo:
    """Folder with computed document count."""

    folder_id: str
    name: str
    relationship: str
    notes: str
    created_at: str
    document_count: int = 0


class FolderDatabase:
    """CRUD for patient folders using LanceDB."""

    TABLE_NAME = "folders"

    def __init__(self, db_dir: str | None = None):
        self.db_dir = Path(db_dir or settings.lancedb_dir)
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self._db: lancedb.DBConnection | None = None

    @property
    def db(self) -> lancedb.DBConnection:
        if self._db is None:
            self._db = lancedb.connect(str(self.db_dir))
        return self._db

    def _get_table(self) -> lancedb.table.Table | None:
        if self.TABLE_NAME in self.db.table_names():
            return self.db.open_table(self.TABLE_NAME)
        return None

    def create_folder(self, name: str, relationship: str = "self", notes: str = "") -> FolderInfo:
        """Create a new patient folder."""
        folder_id = f"fld_{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc).isoformat()

        record = FolderRecord(
            folder_id=folder_id,
            name=name,
            relationship=relationship,
            notes=notes,
            created_at=now,
        )

        if self.TABLE_NAME not in self.db.table_names():
            self.db.create_table(self.TABLE_NAME, [record])
        else:
            table = self.db.open_table(self.TABLE_NAME)
            table.add([record])

        return FolderInfo(
            folder_id=folder_id,
            name=name,
            relationship=relationship,
            notes=notes,
            created_at=now,
            document_count=0,
        )

    def list_folders(self) -> list[FolderInfo]:
        """List all folders with document counts."""
        if self.TABLE_NAME not in self.db.table_names():
            return []

        table = self.db.open_table(self.TABLE_NAME)
        df = table.to_pandas()

        # Get doc counts from documents table
        doc_counts: dict[str, int] = {}
        if "documents" in self.db.table_names():
            docs_table = self.db.open_table("documents")
            docs_df = docs_table.to_pandas(columns=["folder_id"])
            for fid in docs_df["folder_id"]:
                doc_counts[fid] = doc_counts.get(fid, 0) + 1

        results = []
        for _, row in df.iterrows():
            results.append(FolderInfo(
                folder_id=row["folder_id"],
                name=row["name"],
                relationship=row["relationship"],
                notes=row.get("notes", ""),
                created_at=row["created_at"],
                document_count=doc_counts.get(row["folder_id"], 0),
            ))

        return sorted(results, key=lambda f: f.created_at)

    def get_folder(self, folder_id: str) -> FolderInfo | None:
        """Get a single folder by ID."""
        folders = self.list_folders()
        for f in folders:
            if f.folder_id == folder_id:
                return f
        return None

    def update_folder(self, folder_id: str, name: str | None = None, notes: str | None = None) -> FolderInfo | None:
        """Update folder metadata."""
        existing = self.get_folder(folder_id)
        if not existing:
            return None

        table = self._get_table()
        if table is None:
            return None

        # LanceDB doesn't support in-place updates easily, so delete + re-add
        table.delete(f'folder_id = "{folder_id}"')
        updated = FolderRecord(
            folder_id=folder_id,
            name=name or existing.name,
            relationship=existing.relationship,
            notes=notes if notes is not None else existing.notes,
            created_at=existing.created_at,
        )
        table.add([updated])

        return FolderInfo(
            folder_id=folder_id,
            name=name or existing.name,
            relationship=existing.relationship,
            notes=notes if notes is not None else existing.notes,
            created_at=existing.created_at,
            document_count=existing.document_count,
        )

    def delete_folder(self, folder_id: str) -> bool:
        """Delete a folder (does NOT delete its documents — call pipeline for that)."""
        table = self._get_table()
        if table is None:
            return False
        try:
            table.delete(f'folder_id = "{folder_id}"')
            return True
        except Exception:
            return False
"""MedRAG Pipeline — end-to-end: ingest → embed → store → query → answer.

Supports folder-scoped search (per patient) and hereditary cross-family search.
"""

from __future__ import annotations

from medrag.config import settings, ensure_dirs
from medrag.ingestion.parser import parse_pdf, ingest_directory, ParsedDocument
from medrag.embedding.embedder import Embedder
from medrag.storage.db import MedRAGDatabase, SearchResult
from medrag.storage.folders import FolderDatabase, FolderInfo
from medrag.storage.conversations import (
    ConversationDatabase,
    Conversation,
    ChatMessage,
)
from medrag.synthesis.llm import Synthesizer, SynthesisResult
from medrag.synthesis.hereditary_cache import cache_metadata as hereditary_cache_metadata


class MedRAGPipeline:
    """Full Medical RAG pipeline — one object to rule them all."""

    def __init__(self) -> None:
        ensure_dirs()
        self.embedder = Embedder()
        self.database = MedRAGDatabase()
        self.folders = FolderDatabase()
        self.conversations = ConversationDatabase()
        self.synthesizer = Synthesizer()

    # ── Ingestion ──────────────────────────────────────────────────────

    def ingest_file(self, pdf_path: str, folder_id: str = "default") -> ParsedDocument:
        """Parse and embed a single PDF/image, storing it in the database.

        Args:
            pdf_path: Path to the file.
            folder_id: Which patient folder this belongs to.
        """
        print(f"\n[medrag] ═══ Ingesting: {pdf_path} → folder '{folder_id}' ═══")

        # Phase 1: Parse
        doc = parse_pdf(pdf_path)
        doc.folder_id = folder_id
        doc.save()  # persist markdown to disk

        # Phase 2: Embed
        print(f"[medrag] Embedding document ({len(doc.markdown)} chars)...")
        vector = self.embedder.embed(doc.markdown, task="retrieval.passage")

        # Phase 3: Store
        print("[medrag] Indexing in LanceDB...")
        self.database.index_documents([doc], vector.reshape(1, -1), folder_id=folder_id)

        print(f"[medrag] Ingested: {doc.filename} → {doc.doc_id} (folder: {folder_id})")
        return doc

    def ingest_folder(self, directory: str | None = None, folder_id: str = "default") -> list[ParsedDocument]:
        """Parse and embed all PDFs/images in a directory.

        Args:
            directory: Path to directory with files.
            folder_id: Which patient folder these belong to.
        """
        docs = ingest_directory(directory)

        if not docs:
            return []

        # Assign folder_id
        for doc in docs:
            doc.folder_id = folder_id

        print(f"\n[medrag] ═══ Embedding {len(docs)} document(s) for folder '{folder_id}' ═══")
        texts = [doc.markdown for doc in docs]
        vectors = self.embedder.embed_batch(texts, task="retrieval.passage")

        print("[medrag] ═══ Indexing in LanceDB ═══")
        self.database.index_documents(docs, vectors, folder_id=folder_id)

        print(f"\n[medrag] All {len(docs)} document(s) ingested into folder '{folder_id}'")
        return docs

    # ── Querying ───────────────────────────────────────────────────────

    def query(
        self,
        question: str,
        top_k: int = 5,
        folder_id: str | None = None,
        cross_folders: bool = False,
    ) -> SynthesisResult:
        """Ask a question against the document store.

        Args:
            question: User's medical question.
            top_k: Number of documents to retrieve.
            folder_id: If set, only search this person's documents.
                       If None, search all folders (hereditary mode or no folder selected).
            cross_folders: If True, search all folders and use hereditary-aware LLM prompt.

        1. Embed the query
        2. Hybrid search (vector + FTS) via RRF
        3. Feed retrieved docs to LLM for synthesis
        """
        search_folder = folder_id if not cross_folders else None
        mode_label = "hereditary (all folders)" if cross_folders else f"folder '{folder_id}'"
        print(f"\n[medrag] ═══ Query [{mode_label}]: {question} ═══")

        # Check LM Studio connection
        if not self.synthesizer.check_connection():
            raise ConnectionError(
                "LM Studio is not running. Start it and load a model."
            )

        # Step 1: Embed query
        print("[medrag] Embedding query...")
        query_vec = self.embedder.embed(question, task="retrieval.query")

        # Step 2: Hybrid search
        print(f"[medrag] Searching (top {top_k})...")
        results: list[SearchResult] = self.database.search(
            query_vector=query_vec,
            query_text=question,
            limit=top_k,
            folder_id=search_folder,
        )

        if not results:
            print("[medrag] No matching documents found")
            return SynthesisResult(
                answer="No relevant documents found in the database.",
                sources=[],
                model=self.synthesizer.model,
                tokens_used=0,
            )

        print(f"[medrag] Found {len(results)} relevant document(s):")
        for r in results:
            print(f"  - {r.filename} (folder: {r.folder_id}, score: {r.score:.4f})")

        # Step 3: Build folder context for LLM
        folder_context: dict | None = None
        if folder_id:
            folder_info = self.folders.get_folder(folder_id)
            if folder_info:
                folder_context = {
                    "name": folder_info.name,
                    "relationship": folder_info.relationship,
                }

        # For hereditary search, gather all family member info
        if cross_folders:
            all_folders = self.folders.list_folders()
            folder_context = {
                "family_members": [
                    {"name": f.name, "relationship": f.relationship}
                    for f in all_folders
                ]
            }

        # Step 4: Synthesize answer
        print("[medrag] Generating answer...")
        context_docs = [(r.filename, r.markdown, r.folder_id) for r in results]
        result = self.synthesizer.synthesize(
            question,
            context_docs,
            folder_context=folder_context,
            cross_folders=cross_folders,
            query_vector=query_vec if cross_folders else None,
        )

        print(f"[medrag] Answer generated ({result.tokens_used} tokens)")
        return result

    def query_stream(
        self,
        question: str,
        top_k: int = 5,
        folder_id: str | None = None,
        cross_folders: bool = False,
    ):
        """Streaming variant of query — yields source/token/done events."""
        search_folder = folder_id if not cross_folders else None
        mode_label = "hereditary (all folders)" if cross_folders else f"folder '{folder_id}'"
        print(f"\n[medrag] ═══ Stream Query [{mode_label}]: {question} ═══")

        # Embed query
        query_vec = self.embedder.embed(question, task="retrieval.query")

        # Search
        results: list[SearchResult] = self.database.search(
            query_vector=query_vec,
            query_text=question,
            limit=top_k,
            folder_id=search_folder,
        )

        if not results:
            yield {"type": "done", "data": {"model": "", "tokens_used": 0, "message": "No documents found"}}
            return

        # Build folder context
        folder_context: dict | None = None
        if folder_id:
            folder_info = self.folders.get_folder(folder_id)
            if folder_info:
                folder_context = {
                    "name": folder_info.name,
                    "relationship": folder_info.relationship,
                }

        if cross_folders:
            all_folders = self.folders.list_folders()
            folder_context = {
                "family_members": [
                    {"name": f.name, "relationship": f.relationship}
                    for f in all_folders
                ]
            }

        # Stream synthesis
        context_docs = [(r.filename, r.markdown, r.folder_id) for r in results]
        yield from self.synthesizer.synthesize_stream(
            question,
            context_docs,
            folder_context=folder_context,
            cross_folders=cross_folders,
            query_vector=query_vec if cross_folders else None,
        )

    # ── Folder Management ──────────────────────────────────────────────

    def create_folder(self, name: str, relationship: str = "self", notes: str = "") -> FolderInfo:
        """Create a new patient/family member folder."""
        return self.folders.create_folder(name, relationship, notes)

    def list_folders(self) -> list[FolderInfo]:
        """List all folders with document counts."""
        return self.folders.list_folders()

    def get_folder(self, folder_id: str) -> FolderInfo | None:
        """Get a single folder by ID."""
        return self.folders.get_folder(folder_id)

    def update_folder(self, folder_id: str, name: str | None = None, notes: str | None = None) -> FolderInfo | None:
        """Update folder metadata."""
        return self.folders.update_folder(folder_id, name, notes)

    def delete_folder(self, folder_id: str) -> bool:
        """Delete a folder and all its documents + conversations."""
        # Delete all documents in this folder
        doc_count = self.database.delete_folder_documents(folder_id)
        # Delete all conversations
        conv_count = self.conversations.delete_folder_conversations(folder_id)
        # Delete the folder itself
        deleted = self.folders.delete_folder(folder_id)
        if deleted:
            print(f"[medrag] Deleted folder '{folder_id}': {doc_count} docs, {conv_count} conversations")
        return deleted

    # ── Conversation Management ────────────────────────────────────────

    def create_conversation(self, folder_id: str, title: str = "New conversation") -> Conversation:
        """Start a new conversation in a folder."""
        return self.conversations.create_conversation(folder_id, title)

    def add_message(self, folder_id: str, conv_id: str, role: str, content: str, sources: list[str] | None = None) -> Conversation | None:
        """Append a message to a conversation."""
        msg = ChatMessage(role=role, content=content, sources=sources or [])
        return self.conversations.add_message(folder_id, conv_id, msg)

    def load_conversation(self, folder_id: str, conv_id: str) -> Conversation | None:
        """Load a full conversation."""
        return self.conversations.load_conversation(folder_id, conv_id)

    def list_conversations(self, folder_id: str) -> list[dict]:
        """List conversations for a folder."""
        return self.conversations.list_conversations(folder_id)

    def delete_conversation(self, folder_id: str, conv_id: str) -> bool:
        """Delete a conversation."""
        return self.conversations.delete_conversation(folder_id, conv_id)

    # ── Hereditary Data Sync ───────────────────────────────────────────

    def sync_hereditary_data(self, force: bool = False) -> dict:
        """Sync hereditary condition data from MedGen/HPO/GeneReviews.

        Args:
            force: If True, sync even if cache is not stale.

        Returns:
            Dict with sync results.
        """
        from medrag.synthesis.hereditary_sync import run_sync
        return run_sync(force=force)

    # ── Status ─────────────────────────────────────────────────────────

    def status(self) -> dict:
        """Return current pipeline status."""
        hereditary_meta = hereditary_cache_metadata()
        return {
            "documents_indexed": self.database.count(),
            "documents": self.database.list_documents(),
            "folders": len(self.folders.list_folders()),
            "embedding_model": self.embedder.model_name,
            "llm_model": self.synthesizer.model,
            "lmstudio_url": self.synthesizer.base_url,
            "db_path": str(self.database.db_dir),
            "hereditary_cache": hereditary_meta,
        }
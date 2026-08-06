"""Hugging Face Corpus Ingestion for MedRAG.

Downloads and ingests medical datasets from the MedRAG Hugging Face repository
(e.g., textbooks, statpearls, pubmed).
"""

from __future__ import annotations

from rich.console import Console
from rich.progress import track

from medrag.ingestion.parser import ParsedDocument
from medrag.pipeline import MedRAGPipeline

try:
    from datasets import load_dataset
except ImportError:
    load_dataset = None  # type: ignore

console = Console()

from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

try:
    from huggingface_hub import disable_progress_bars
    disable_progress_bars()
except ImportError:
    pass


class CorpusIngestor:
    def __init__(self, pipeline: MedRAGPipeline | None = None):
        self.pipeline = pipeline or MedRAGPipeline()
        if load_dataset is None:
            raise ImportError(
                "The 'datasets' library is required to download the MedRAG corpus. "
                "Please run: pip install datasets"
            )

    def ingest_subset(self, subset: str, limit: int = 1000, batch_size: int = 64) -> None:
        """Download and ingest a MedRAG corpus subset.
        
        Args:
            subset: The HF dataset subset (e.g., 'textbooks', 'statpearls').
            limit: Maximum number of snippets to ingest (0 means all).
            batch_size: How many documents to embed/index at once.
        """
        console.print(f"\n[bold blue][MedRAG Corpus][/bold blue] Loading subset: [green]{subset}[/green]")
        
        # Always use streaming so we ingest on-the-fly without waiting for multi-GB upfront download
        streaming = True
        dataset_name = f"MedRAG/{subset}"
        try:
            assert load_dataset is not None
            dataset = load_dataset(
                dataset_name, 
                split="train", 
                streaming=streaming,
                cache_dir="data/raw/downloads/Corpus"
            )
        except Exception as e:
            console.print(f"[bold red]Failed to load corpus subset '{subset}': {e}[/bold red]")
            return

        folder_id = f"corpus_{subset}"
        # Ensure the folder exists in our metadata DB
        if not self.pipeline.get_folder(folder_id):
            try:
                self.pipeline.create_folder(name=f"Corpus: {subset.title()}", notes=f"MedRAG HF Dataset: {subset}")
            except Exception:
                pass

        # Batch processing loop
        docs_batch: list[ParsedDocument] = []
        texts_batch: list[str] = []
        
        total_ingested = 0
        total_items = limit if limit > 0 else None
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue][MedRAG Corpus][/bold blue] Ingesting {task.fields[subset]}..."),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("ingest", total=total_items, subset=subset)
            
            for item in dataset:
                if limit > 0 and total_ingested >= limit:
                    break
                    
                # item usually has: id, title, content, contents
                item_id = str(item.get("id", f"snippet_{total_ingested}"))
                title = item.get("title", "Untitled")
                content = item.get("content", "")
                
                if not content.strip():
                    continue
                    
                # Format as markdown
                markdown = f"# {title}\n\n{content}"
                # Ensure doc_id is safe and unique
                doc_id = f"hf_{item_id}".replace("/", "_").replace(":", "_").replace(" ", "_")
                
                doc = ParsedDocument(
                    doc_id=doc_id,
                    filename=f"{item_id}.md",
                    markdown=markdown,
                    pages=1,
                    folder_id=folder_id,
                    metadata={"source": f"hf:MedRAG/corpus/{subset}", "title": title}
                )
                
                docs_batch.append(doc)
                texts_batch.append(markdown)
                
                if len(docs_batch) >= batch_size:
                    self._process_batch(docs_batch, texts_batch, folder_id)
                    total_ingested += len(docs_batch)
                    progress.update(task, completed=total_ingested)
                    docs_batch.clear()
                    texts_batch.clear()

            # Process remaining
            if docs_batch:
                self._process_batch(docs_batch, texts_batch, folder_id)
                total_ingested += len(docs_batch)
                progress.update(task, completed=total_ingested)
            
        console.print(f"[bold green]Successfully ingested {total_ingested} documents into folder '{folder_id}'![/bold green]")

    def _process_batch(self, docs: list[ParsedDocument], texts: list[str], folder_id: str) -> None:
        """Embed and index a batch of documents."""
        # 1. Embed
        vectors = self.pipeline.embedder.embed_batch(texts, task="retrieval.passage")
        # 2. Index
        self.pipeline.database.index_documents(docs, vectors, folder_id=folder_id)

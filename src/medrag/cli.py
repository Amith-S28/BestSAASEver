"""MedRAG CLI — command-line interface for the Medical RAG pipeline."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

app = typer.Typer(
    name="medrag",
    help="Local Medical RAG System — fully offline, privacy-preserving",
)
console = Console()


@app.command()
def ingest(
    path: str = typer.Argument(..., help="PDF file or directory containing PDFs"),
    engine: str = typer.Option(None, "--engine", "-e", help="OCR engine: marker or pymupdf"),
) -> None:
    """Ingest PDF files into the RAG database."""
    from medrag.pipeline import MedRAGPipeline
    from medrag.config import settings

    if engine:
        import os
        os.environ["OCR_ENGINE"] = engine

    pipeline = MedRAGPipeline()

    from pathlib import Path

    if Path(path).is_file():
        pipeline.ingest_file(path)
    elif Path(path).is_dir():
        pipeline.ingest_folder(path)
    else:
        console.print(f"[red]Error:[/red] {path} is not a valid file or directory")
        raise typer.Exit(1)


@app.command()
def query(
    question: str = typer.Argument(..., help="Your medical question"),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Number of documents to retrieve"),
) -> None:
    """Ask a question against your medical document database."""
    from medrag.pipeline import MedRAGPipeline

    pipeline = MedRAGPipeline()
    result = pipeline.query(question, top_k=top_k)

    # Display answer
    console.print()
    console.print(Panel(
        Markdown(result.answer),
        title="[bold green]Answer[/bold green]",
        border_style="green",
    ))

    # Display sources
    if result.sources:
        console.print("\n[bold]Sources:[/bold]")
        for src in result.sources:
            console.print(f"  [Source] {src}")

    console.print(f"\n[dim]Model: {result.model} | Tokens: {result.tokens_used}[/dim]")


@app.command()
def status() -> None:
    """Show current pipeline status and configuration."""
    from medrag.pipeline import MedRAGPipeline

    pipeline = MedRAGPipeline()
    info = pipeline.status()

    console.print("\n[bold]MedRAG Pipeline Status[/bold]\n")
    console.print(f"  Documents indexed:  [cyan]{info['documents_indexed']}[/cyan]")
    console.print(f"  Embedding model:    [cyan]{info['embedding_model']}[/cyan]")
    console.print(f"  LLM model:         [cyan]{info['llm_model']}[/cyan]")
    console.print(f"  LM Studio URL:      [cyan]{info['lmstudio_url']}[/cyan]")
    console.print(f"  Database path:      [cyan]{info['db_path']}[/cyan]")

    if info["documents"]:
        console.print("\n[bold]Indexed Documents:[/bold]")
        for doc in info["documents"]:
            console.print(f"  [Doc] {doc}")


@app.command()
def serve(
    host: str = typer.Option(None, "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(None, "--port", "-p", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for dev"),
) -> None:
    """Start the MedRAG web server."""
    import uvicorn
    from medrag.config import settings

    h = host or settings.web_host
    p = port or settings.web_port

    console.print(f"\n[bold][Server] MedRAG Web Server[/bold]")
    console.print(f"   -> [cyan]http://{h}:{p}[/cyan]")
    console.print(f"   -> All data stays local\n")

    import sys
    from pathlib import Path
    src_dir = str(Path(__file__).parent.parent)
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    if reload:
        uvicorn.run(
            "medrag.web.app:app",
            host=h,
            port=p,
            reload=reload,
            log_level="info",
        )
    else:
        from medrag.web.app import app as web_app
        uvicorn.run(
            web_app,
            host=h,
            port=p,
            log_level="info",
        )


@app.command()
def check() -> None:
    """Check if LM Studio is running and model is loaded."""
    from medrag.synthesis.llm import Synthesizer

    synth = Synthesizer()
    connected = synth.check_connection()

    if connected:
        console.print("\n[bold green][OK] LM Studio is running and model is loaded[/bold green]")
    else:
        console.print("\n[bold red][ERROR] LM Studio is not reachable[/bold red]")
        console.print("\nTo fix:")
        console.print("  1. Open LM Studio")
        console.print("  2. Load [cyan]Qwen3-9B-Instruct[/cyan] (or similar)")
        console.print("  3. Start the local server on port 1234")


@app.command()
def download(
    count: int = typer.Option(50, "--count", "-n", help="Number of documents to download/generate"),
    clean: bool = typer.Option(False, "--clean", help="Delete existing folders and documents first"),
) -> None:
    """Download medical PDFs from NIH PMC and generate synthetic test docs.

    Fetches open-access articles from PubMed Central, organizes them into
    simulated family folders (Me, Mom, Dad, Sister, Spouse), and auto-ingests
    into MedRAG. Falls back to synthetic lab reports if PMC downloads fail.
    """
    from medrag.download import run_download, FOLDER_ORDER, get_folder_info

    console.print("\n[bold][Downloader] MedRAG Document Downloader[/bold]")
    console.print(f"   Target: [cyan]{count}[/cyan] documents")
    if clean:
        console.print("   Mode: [red]clean[/red] (existing data will be deleted)")
    console.print()

    result = run_download(count=count, clean=clean)

    # Display summary
    console.print()
    console.print(Panel(
        "\n".join([
            f"[bold]Total ingested:[/bold] [green]{result['total_ingested']}[/green]",
            "",
            *[
                f"  {get_folder_info(k)['name']}: [cyan]{v}[/cyan] documents"
                for k, v in result["per_folder"].items()
                if v > 0
            ],
            "",
            f"[dim]Failures: {result['failures']}[/dim]" if result["failures"] else "",
        ]),
        title="[bold]Download Summary[/bold]",
        border_style="green" if result["failures"] == 0 else "yellow",
    ))


@app.command()
def synthea(
    csv_dir: str = typer.Option(None, "--csv-dir", "-d", help="Path to Synthea CSV directory (downloads sample if not provided)"),
    limit: int = typer.Option(10, "--limit", "-l", help="Max number of patients to process"),
) -> None:
    """Process Synthea CSV data and generate encounter PDFs.
    
    Generates realistic medical PDFs (one per encounter) from Synthea CSV
    outputs, saves them to a 'SyntheticData' folder, and ingests them into MedRAG.
    """
    from medrag.synthea import SyntheaIngestor
    
    console.print("\n[bold][Synthea] MedRAG Synthetic Data Ingestor[/bold]")
    
    ingestor = SyntheaIngestor(output_dir="SyntheticData")
    ingestor.process(csv_dir=csv_dir, limit_patients=limit)


@app.command()
def corpus(
    subset: str = typer.Argument("textbooks", help="Hugging Face corpus subset (e.g., textbooks, statpearls, pubmed)"),
    limit: int = typer.Option(1000, "--limit", "-l", help="Max number of snippets to ingest (0 to download ALL)"),
    batch_size: int = typer.Option(64, "--batch-size", "-b", help="Number of documents per embedding batch"),
) -> None:
    """Download and ingest MedRAG Hugging Face Corpus datasets.
    
    Streams pre-processed medical datasets (like textbooks or PubMed) directly
    from Hugging Face and ingests them into the local LanceDB vector store.
    """
    try:
        from medrag.corpus import CorpusIngestor
    except ImportError as e:
        console.print(f"[bold red]Error loading corpus module:[/bold red] {e}")
        raise typer.Exit(1)
        
    ingestor = CorpusIngestor()
    ingestor.ingest_subset(subset, limit=limit, batch_size=batch_size)


if __name__ == "__main__":
    app()
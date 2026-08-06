"""Document ingestion engine — converts PDFs and images into structured Markdown.

Supports PDFs AND photos (JPG, PNG, TIFF, etc.) — snap a pic of a document
and feed it straight in.

Backends (tried in priority order):
  1. chandra (default): SOTA vision-language OCR. Handles images natively.
  2. chandra-cli: Simpler CLI wrapper around Chandra.
  3. pymupdf: Fast text-only extraction (PDFs only, no image support).
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from dataclasses import dataclass, field

from medrag.config import settings

# Supported file extensions
SUPPORTED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}


@dataclass
class ParsedDocument:
    """A fully parsed medical document ready for embedding."""

    doc_id: str
    filename: str
    markdown: str
    pages: int
    folder_id: str = "default"  # which patient/person this belongs to
    metadata: dict = field(default_factory=dict)

    def save(self, output_dir: Path | None = None) -> Path:
        """Persist parsed markdown + metadata to disk."""
        out = Path(output_dir or settings.processed_dir)
        out.mkdir(parents=True, exist_ok=True)
        md_path = out / f"{self.doc_id}.md"
        meta_path = out / f"{self.doc_id}.meta.json"

        md_path.write_text(self.markdown, encoding="utf-8")
        meta_path.write_text(
            json.dumps(
                {"doc_id": self.doc_id, "filename": self.filename,
                 "pages": self.pages, "metadata": self.metadata},
                indent=2,
            ),
            encoding="utf-8",
        )
        return md_path


def _stable_id(content: str, filename: str) -> str:
    """Generate a stable document ID from content hash + filename."""
    digest = hashlib.sha256((content + filename).encode()).hexdigest()[:12]
    return f"doc_{digest}"


def _clean_markdown(raw: str) -> str:
    """Post-process extracted markdown for cleaner RAG input."""
    # Collapse 3+ blank lines into 2
    text = re.sub(r"\n{3,}", "\n\n", raw)
    # Remove stray control characters
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    # Normalize unicode dashes
    text = text.replace("–", "-").replace("—", "--")
    return text.strip()


# ── Chandra OCR 2 Backend (default, best quality) ──────────────────────────


def parse_with_chandra(file_path: Path) -> ParsedDocument:
    """Extract text using Chandra OCR 2 — SOTA vision-language OCR.

    Handles PDFs AND images (JPG, PNG, etc.). Tables, handwriting, math, 90+ languages.
    """
    from PIL import Image as PILImage
    from chandra.model.schema import BatchInputItem
    from chandra.output import parse_markdown

    img = PILImage.open(str(file_path)).convert("RGB")

    # Try MLX backend first (Apple Silicon optimized), then HuggingFace
    try:
        from chandra.model.mlx import generate_mlx

        batch = [BatchInputItem(image=img, prompt_type="ocr_layout")]
        result = generate_mlx(batch)[0]
        markdown_text = parse_markdown(result.raw)
        engine_used = "chandra-mlx"
    except (ImportError, Exception):
        # Fall back to HuggingFace transformers backend
        from chandra.model.hf import generate_hf
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor

        model = AutoModelForImageTextToText.from_pretrained(
            "datalab-to/chandra-ocr-2",
            torch_dtype=torch.bfloat16,
            device_map="auto",
        )
        model.eval()
        model.processor = AutoProcessor.from_pretrained("datalab-to/chandra-ocr-2")
        model.processor.tokenizer.padding_side = "left"

        batch = [BatchInputItem(image=img, prompt_type="ocr_layout")]
        result = generate_hf(batch, model)[0]
        markdown_text = parse_markdown(result.raw)
        engine_used = "chandra-hf"

    full_markdown = _clean_markdown(markdown_text)
    pages = full_markdown.count("\n---\n") + 1

    return ParsedDocument(
        doc_id=_stable_id(full_markdown, file_path.name),
        filename=file_path.name,
        markdown=full_markdown,
        pages=max(pages, 1),
        metadata={"engine": engine_used, "source": str(file_path)},
    )


# ── Chandra CLI Backend (simplest, uses pip-installed chandra-ocr) ──────────


def parse_with_chandra_cli(file_path: Path, output_dir: Path | None = None) -> ParsedDocument:
    """Use the chandra-ocr CLI to parse a file (PDF or image).

    This is the simplest way to use Chandra — it handles model loading internally.
    """
    import subprocess
    import tempfile

    out_dir = Path(output_dir or tempfile.mkdtemp(prefix="medrag_chandra_"))
    out_dir.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        ["chandra", str(file_path), str(out_dir)],
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Chandra CLI failed: {result.stderr}")

    # Find the output markdown file (CLI creates subdirectories per input)
    md_files = list(out_dir.rglob("*.md"))
    if not md_files:
        raise RuntimeError(f"No markdown output from Chandra for {file_path}")

    markdown_text = md_files[0].read_text(encoding="utf-8")
    full_markdown = _clean_markdown(markdown_text)
    pages = full_markdown.count("\n---\n") + 1

    return ParsedDocument(
        doc_id=_stable_id(full_markdown, file_path.name),
        filename=file_path.name,
        markdown=full_markdown,
        pages=max(pages, 1),
        metadata={"engine": "chandra-cli", "source": str(file_path)},
    )


# ── PyMuPDF Backend (fast fallback, PDFs only) ──────────────────────────────


def parse_with_pymupdf(pdf_path: Path) -> ParsedDocument:
    """Extract text from a PDF using PyMuPDF (fast, no ML model needed).

    Good for text-based PDFs. Struggles with scanned documents and complex layouts.
    Does NOT support image files — use Chandra for photos.
    """
    import fitz  # pymupdf

    doc = fitz.open(str(pdf_path))
    pages_text: list[str] = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text", sort=True)
        if text.strip():
            pages_text.append(f"## Page {page_num + 1}\n\n{text}")

    doc.close()
    full_markdown = _clean_markdown("\n\n".join(pages_text))

    return ParsedDocument(
        doc_id=_stable_id(full_markdown, pdf_path.name),
        filename=pdf_path.name,
        markdown=full_markdown,
        pages=len(pages_text),
        metadata={"engine": "pymupdf", "source": str(pdf_path)},
    )


# ── Unified Entry Point ────────────────────────────────────────────────────


def parse_file(file_path: str | Path, engine: str | None = None) -> ParsedDocument:
    """Parse a PDF or image file into structured Markdown.

    Args:
        file_path: Path to a PDF, JPG, PNG, TIFF, BMP, or WebP file.
        engine: "chandra", "chandra-cli", or "pymupdf" (PDFs only).
                 Defaults to settings.ocr_engine.

    Returns:
        ParsedDocument with markdown content and metadata.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = file_path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {suffix!r}. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    engine = engine or settings.ocr_engine
    is_image = suffix in {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}

    # Images require Chandra — pymupdf can't handle them
    if is_image and engine == "pymupdf":
        print(f"[medrag] ⚠️  Image file detected ({suffix}). pymupdf can't handle images — using chandra-cli instead.")
        engine = "chandra-cli"

    if engine in ("chandra",):
        try:
            return parse_with_chandra(file_path)
        except ImportError:
            print("[medrag] chandra-ocr not installed, trying chandra-cli...")
            try:
                return parse_with_chandra_cli(file_path)
            except (ImportError, FileNotFoundError):
                if is_image:
                    raise RuntimeError(
                        f"Cannot process image {file_path.name} without Chandra OCR. "
                        "Install with: pip install chandra-ocr[all]"
                    )
                print("[medrag] chandra-cli not found, falling back to pymupdf")
                return parse_with_pymupdf(file_path)
        except Exception as e:
            if is_image:
                raise RuntimeError(f"Chandra OCR failed on image {file_path.name}: {e}")
            print(f"[medrag] Chandra OCR failed: {e}, falling back to pymupdf")
            return parse_with_pymupdf(file_path)

    elif engine == "chandra-cli":
        try:
            return parse_with_chandra_cli(file_path)
        except (ImportError, FileNotFoundError, RuntimeError) as e:
            if is_image:
                raise RuntimeError(f"Cannot process image {file_path.name}: {e}")
            print(f"[medrag] chandra-cli failed: {e}, falling back to pymupdf")
            return parse_with_pymupdf(file_path)

    elif engine == "pymupdf":
        if is_image:
            raise ValueError(
                f"pymupdf cannot process image files ({suffix}). "
                "Use OCR_ENGINE=chandra to process photos."
            )
        return parse_with_pymupdf(file_path)

    else:
        raise ValueError(
            f"Unknown OCR engine: {engine!r}. "
            "Use 'chandra', 'chandra-cli', or 'pymupdf'."
        )


# Keep backward compatibility
parse_pdf = parse_file


def ingest_directory(directory: str | Path | None = None, engine: str | None = None) -> list[ParsedDocument]:
    """Parse all PDFs and images in a directory and save results.

    Supports: PDF, JPG, JPEG, PNG, TIFF, BMP, WebP

    Args:
        directory: Directory containing files. Defaults to settings.raw_dir.
        engine: OCR engine override.

    Returns:
        List of parsed documents.
    """
    directory = Path(directory or settings.raw_dir)
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    files: list[Path] = []
    for ext in sorted(SUPPORTED_EXTENSIONS):
        files.extend(sorted(directory.glob(f"*{ext}")))

    # Deduplicate (in case of overlapping globs)
    files = sorted(set(files))

    if not files:
        print(f"[medrag] No files found in {directory}")
        print(f"[medrag] Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
        return []

    results: list[ParsedDocument] = []
    for f in files:
        print(f"[medrag] Parsing {f.name}...")
        doc = parse_file(f, engine=engine)
        saved = doc.save()
        print(f"[medrag]   -> {doc.doc_id}.md ({doc.pages} pages, saved to {saved})")
        results.append(doc)

    print(f"\n[medrag] Ingested {len(results)} document(s)")
    return results
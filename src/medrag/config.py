"""Configuration loader — reads .env and provides typed settings."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Load .env from project root
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


class Settings(BaseSettings):
    """All runtime configuration, sourced from environment variables or .env."""

    # ── HuggingFace ──────────────────────────────────────────────────────
    hf_token: str | None = Field(
        default=None,
        description="HuggingFace token for faster model downloads",
    )

    # ── LM Studio (Qwen 3.5 9B Instruct) ──────────────────────────────
    lmstudio_base_url: str = Field(
        default="http://127.0.0.1:1234/v1",
        description="LM Studio OpenAI-compatible server URL",
    )
    lmstudio_model: str = Field(
        default="google/gemma-4-e4b",
        description="Model identifier loaded in LM Studio",
    )
    lmstudio_max_context: int = Field(
        default=8192,
        description="Max tokens to send to LLM per request",
    )
    lmstudio_temperature: float = Field(
        default=0.3,
        description="Sampling temperature for synthesis",
    )

    # ── Embeddings ─────────────────────────────────────────────────────
    embedding_model: str = Field(
        default="BAAI/bge-small-en-v1.5",
        description="HuggingFace model ID for embeddings (local)",
    )
    embedding_dim: int = Field(
        default=384,
        description="Output dimension of the embedding model",
    )

    # ── LanceDB ────────────────────────────────────────────────────────
    lancedb_dir: str = Field(
        default="./data/lancedb",
        description="Directory for LanceDB persistent storage",
    )

    # ── OCR / Parsing ──────────────────────────────────────────────────
    ocr_engine: str = Field(
        default="chandra",
        description="OCR engine: 'chandra' (best, SOTA), 'chandra-cli' (simpler), 'marker', or 'pymupdf' (fast fallback)",
    )

    # ── Web Server ──────────────────────────────────────────────────────
    web_host: str = Field(
        default="127.0.0.1",
        description="Host for the web server",
    )
    web_port: int = Field(
        default=8000,
        description="Port for the web server",
    )
    max_upload_size_mb: int = Field(
        default=100,
        description="Maximum file upload size in MB",
    )

    # ── Paths ──────────────────────────────────────────────────────────
    data_dir: str = Field(
        default="./data",
        description="Root data directory",
    )
    raw_dir: str = Field(
        default="./data/raw",
        description="Inbound PDF / scan directory",
    )
    processed_dir: str = Field(
        default="./data/processed",
        description="Extracted markdown output directory",
    )
    conversations_dir: str = Field(
        default="./data/conversations",
        description="Directory for conversation history JSON files",
    )

    # ── Hereditary Data Sync ─────────────────────────────────────────
    hereditary_cache_dir: str = Field(
        default="./data/cache/hereditary",
        description="Directory for cached hereditary condition data from MedGen/HPO",
    )
    hereditary_sync_interval_days: int = Field(
        default=7,
        description="Days between hereditary data sync attempts (MedGen updates weekly)",
    )
    hereditary_max_conditions_in_prompt: int = Field(
        default=15,
        description="Max conditions to include in LLM prompt (selected by relevance to query)",
    )
    ncbi_api_key: str | None = Field(
        default=None,
        description="Optional NCBI API key (increases MedGen rate from 3/s to 10/s)",
    )
    hereditary_sync_on_startup: bool = Field(
        default=False,
        description="Check for hereditary data updates on startup",
    )

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()

# Set HF token for all downloads if provided
if settings.hf_token:
    os.environ["HF_TOKEN"] = settings.hf_token


def ensure_dirs() -> None:
    """Create all required directories if they don't exist."""
    for d in [
        settings.data_dir, settings.raw_dir, settings.processed_dir,
        settings.lancedb_dir, settings.conversations_dir,
        settings.hereditary_cache_dir,
    ]:
        Path(d).mkdir(parents=True, exist_ok=True)
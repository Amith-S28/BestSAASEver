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

    # ── Operational Mode ─────────────────────────────────────────────
    mode: str = Field(
        default="cloud",
        description="System mode: 'local' (offline LM Studio) or 'cloud' (OpenRouter/NIM)",
    )

    # ── HuggingFace ──────────────────────────────────────────────────
    hf_token: str | None = Field(
        default=None,
        description="HuggingFace token for faster model downloads",
    )

    # ── Cloud API Key ────────────────────────────────────────────────
    openai_api_key: str | None = Field(
        default=None,
        description="API key for cloud LLM/reranker (OpenRouter, NVIDIA NIM)",
    )

    # ── LLM Server / Router ──────────────────────────────────────────
    lmstudio_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="Cloud LLM endpoint (OpenRouter) or local LM Studio URL",
    )
    lmstudio_model: str = Field(
        default="inclusionai/ling-3.0-flash:free",
        description="Model identifier for LLM synthesis (Tier 1 default)",
    )
    lmstudio_max_context: int = Field(
        default=8192,
        description="Max tokens to send to LLM per request",
    )
    lmstudio_temperature: float = Field(
        default=0.3,
        description="Sampling temperature for synthesis",
    )

    router_mode: str = Field(
        default="auto",
        description="LLM routing strategy: 'auto', 'tier1', 'tier2', 'tier3'",
    )

    # ── Embeddings ────────────────────────────────────────────────────
    embedding_model: str = Field(
        default="jinaai/jina-embeddings-v5-omni-small",
        description="HuggingFace model ID for embeddings (local)",
    )
    embedding_dim: int = Field(
        default=1024,
        description="Output dimension of the embedding model",
    )

    # ── Compute Device ───────────────────────────────────────────────
    compute_device: str = Field(
        default="auto",
        description="Compute device: 'auto', 'cpu', 'cuda', 'mps', 'dml'",
    )

    # ── Reranker ─────────────────────────────────────────────────────
    reranker_enabled: bool = Field(
        default=False,
        description="Enable NVIDIA NIM reranking before LLM synthesis",
    )
    reranker_base_url: str = Field(
        default="https://integrate.api.nvidia.com/v1",
        description="NVIDIA NIM reranker API endpoint",
    )
    reranker_model: str = Field(
        default="nvidia/nv-rerankqa-mistral-4b-v3",
        description="Reranker model identifier",
    )
    reranker_api_key: str | None = Field(
        default=None,
        description="API key for NVIDIA NIM reranker. Falls back to openai_api_key if not set.",
    )

    # ── LanceDB ────────────────────────────────────────────────────────
    lancedb_dir: str = Field(
        default="./data/lancedb",
        description="Directory for LanceDB persistent storage",
    )

    # ── OCR / Parsing ──────────────────────────────────────────────────
    ocr_engine: str = Field(
        default="chandra",
        description="OCR engine",
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
        description="Days between hereditary data sync attempts",
    )
    hereditary_max_conditions_in_prompt: int = Field(
        default=15,
        description="Max conditions to include in LLM prompt",
    )
    ncbi_api_key: str | None = Field(
        default=None,
        description="Optional NCBI API key",
    )
    hereditary_sync_on_startup: bool = Field(
        default=False,
        description="Check for hereditary data updates on startup",
    )

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()

# Support MODE=local override
if settings.mode.lower() == "local":
    settings.lmstudio_base_url = "http://127.0.0.1:1234/v1"

# Auto-correct LM Studio base_url if missing /v1 suffix
if not settings.lmstudio_base_url.rstrip("/").endswith("/v1"):
    settings.lmstudio_base_url = settings.lmstudio_base_url.rstrip("/") + "/v1"

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

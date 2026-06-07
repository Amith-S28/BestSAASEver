"""FastAPI application factory — wires up all routes and static files."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from medrag.config import settings, ensure_dirs
from medrag.web.routers import status, documents, queries, chat, folders, conversations


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: ensure dirs exist, pre-warm pipeline."""
    ensure_dirs()
    # Pre-warm: trigger embedding model load on startup
    from medrag.web.deps import get_pipeline
    print("[medrag] Warming up pipeline...")
    pipeline = get_pipeline()
    print(f"[medrag] Ready — {pipeline.database.count()} document(s) indexed, {len(pipeline.list_folders())} folder(s)")
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="MedRAG",
        description="Local Medical RAG System — fully offline, privacy-preserving",
        version="0.2.0",
        lifespan=lifespan,
    )

    # CORS — allow localhost for dev
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routers
    app.include_router(status.router)
    app.include_router(folders.router)
    app.include_router(conversations.router)
    app.include_router(documents.router)
    app.include_router(queries.router)
    app.include_router(chat.router)

    # Serve static frontend files
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app


app = create_app()
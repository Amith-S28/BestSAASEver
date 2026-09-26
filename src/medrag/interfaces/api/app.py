"""FastAPI Institutional SaaS Application Factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from medrag.domain.exceptions import ClinicalException
from medrag.interfaces.api.dependencies import get_services
from medrag.interfaces.api.exception_handler import (
    clinical_exception_handler,
    generic_exception_handler,
)
from medrag.interfaces.api.middleware import TenantScopeMiddleware
from medrag.interfaces.api.routes import admin, clinical, evidence, health, patients


def create_app() -> FastAPI:
    """Create and configure FastAPI institutional platform instance."""
    app = FastAPI(
        title="MedRAG Clinical Intelligence API",
        description="Institutional-Grade Clinical AI Intelligence SaaS Platform with Deterministic NLI Verification",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS configuration for institutional web client
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Institutional Multi-Tenant Gateway Middleware
    services = get_services()
    app.add_middleware(
        TenantScopeMiddleware,
        auth_provider=services.auth_provider,
    )

    # Exception Handlers
    app.add_exception_handler(ClinicalException, clinical_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # Include API Routers
    app.include_router(health.router)
    app.include_router(clinical.router)
    app.include_router(patients.router)
    app.include_router(evidence.router)
    app.include_router(admin.router)

    # Static Assets & Clinician Workspace UI
    from pathlib import Path
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    static_dir = Path(__file__).resolve().parent.parent / "web" / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        @app.get("/", include_in_schema=False)
        async def serve_index():
            return FileResponse(static_dir / "index.html")

    return app


app = create_app()

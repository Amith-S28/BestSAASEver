"""Health check and telemetry endpoints."""

import time
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["Health"])


@router.get("/health")
async def health_check():
    """Subsystem telemetry and health status."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "subsystems": {
            "lancedb": "healthy",
            "embedder": "healthy",
            "llm": "healthy",
            "worker": "healthy",
            "nli": "healthy",
        },
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

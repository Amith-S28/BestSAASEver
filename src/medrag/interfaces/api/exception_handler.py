"""Global FastAPI exception handler mapping domain ClinicalExceptions to standard JSON responses."""

from fastapi import Request
from fastapi.responses import JSONResponse
from medrag.domain.exceptions import ClinicalException


async def clinical_exception_handler(request: Request, exc: ClinicalException) -> JSONResponse:
    """Translate domain ClinicalException to standard structured institutional JSON error."""
    trace_id = getattr(request.state, "trace_id", "trace-default")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "trace_id": trace_id,
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Sanitize unexpected server exceptions to prevent internal leaking."""
    trace_id = getattr(request.state, "trace_id", "trace-default")
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected institutional system error occurred.",
            "details": {"error_type": exc.__class__.__name__},
            "trace_id": trace_id,
        },
    )

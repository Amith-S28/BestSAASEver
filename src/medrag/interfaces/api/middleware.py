"""TenantScopeMiddleware enforcing institutional multi-tenancy and authentication boundaries."""

import uuid
from typing import Callable, Set
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from medrag.ports.auth import IAuthProvider


class TenantScopeMiddleware(BaseHTTPMiddleware):
    """Enforces authentication and tenant isolation at the outer gateway boundary."""

    def __init__(
        self,
        app,
        auth_provider: IAuthProvider,
        public_paths: Set[str] = None,
    ) -> None:
        super().__init__(app)
        self.auth_provider = auth_provider
        self.public_paths = public_paths or {
            "/api/v1/health",
            "/docs",
            "/redoc",
            "/openapi.json",
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        trace_id = str(uuid.uuid4())
        request.state.trace_id = trace_id

        # Skip auth for public endpoints or static UI files
        if (
            request.url.path in self.public_paths
            or request.url.path.startswith("/static")
            or request.url.path == "/"
        ):
            request.state.user = None
            request.state.tenant_id = "public"
            return await call_next(request)

        # Extract auth credentials
        auth_header = request.headers.get("Authorization")
        api_key_header = request.headers.get("X-API-Key")

        authenticated_user = None

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            authenticated_user = await self.auth_provider.validate_token(token)
        elif api_key_header:
            api_key = api_key_header.strip()
            authenticated_user = await self.auth_provider.validate_api_key(api_key)

        if not authenticated_user:
            return JSONResponse(
                status_code=401,
                content={
                    "error_code": "UNAUTHENTICATED",
                    "message": "Valid institutional Bearer token or X-API-Key required.",
                    "details": {},
                    "trace_id": trace_id,
                },
            )

        # Inject security context into request state
        request.state.user = authenticated_user
        request.state.tenant_id = authenticated_user.tenant_id
        request.state.clinic_id = authenticated_user.clinic_id
        request.state.user_id = authenticated_user.user_id
        request.state.role = authenticated_user.role
        request.state.scopes = authenticated_user.scopes

        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id
        return response

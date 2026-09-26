"""Authentication and authorization service implementing IAuthProvider."""

import time
from typing import Dict, List, Optional
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import JWTError, jwt
from medrag.domain.exceptions import TenantIsolationViolationException
from medrag.ports.auth import AuthenticatedUser, IAuthProvider

# Institutional Role-to-Scope mapping
ROLE_SCOPES: Dict[str, List[str]] = {
    "clinician": [
        "patient:read",
        "patient:write",
        "query:execute",
        "query:view_history",
        "evidence:view",
    ],
    "cmo": [
        "patient:read",
        "patient:write",
        "patient:delete",
        "query:execute",
        "query:view_history",
        "evidence:view",
        "audit:read",
        "audit:export",
    ],
    "auditor": [
        "query:view_history",
        "evidence:view",
        "audit:read",
        "audit:export",
    ],
    "researcher": [
        "query:execute",
        "query:view_history",
        "evidence:view",
    ],
    "admin": [
        "patient:read",
        "patient:write",
        "patient:delete",
        "query:execute",
        "query:view_history",
        "evidence:view",
        "audit:read",
        "audit:export",
        "tenant:manage",
        "user:manage",
        "corpus:manage",
        "system:health",
    ],
}


class JWTAuthProvider(IAuthProvider):
    """Institutional JWT and API-key verification engine."""

    def __init__(
        self,
        secret_key: str = "medrag-institutional-dev-secret-key-32bytes-min!",
        algorithm: str = "HS256",
        token_expire_seconds: int = 3600 * 8,  # 8 hour clinical shift
    ) -> None:
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_expire_seconds = token_expire_seconds
        self.hasher = PasswordHasher()
        # In-memory API key registry: api_key -> AuthenticatedUser
        self._api_keys: Dict[str, AuthenticatedUser] = {}
        # Pre-seed standard development / test keys
        self.register_api_key(
            api_key="test-clinician-key",
            user=AuthenticatedUser(
                user_id="usr-dr-smith",
                tenant_id="tenant-general-hospital",
                clinic_id="clinic-main",
                role="clinician",
                scopes=ROLE_SCOPES["clinician"],
            ),
        )
        self.register_api_key(
            api_key="test-cmo-key",
            user=AuthenticatedUser(
                user_id="usr-cmo-dr-chen",
                tenant_id="tenant-general-hospital",
                clinic_id="clinic-main",
                role="cmo",
                scopes=ROLE_SCOPES["cmo"],
            ),
        )
        self.register_api_key(
            api_key="test-admin-key",
            user=AuthenticatedUser(
                user_id="usr-admin",
                tenant_id="tenant-general-hospital",
                clinic_id="clinic-admin",
                role="admin",
                scopes=ROLE_SCOPES["admin"],
            ),
        )

    def hash_password(self, password: str) -> str:
        """Hash a password using Argon2id."""
        return self.hasher.hash(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against Argon2id hash."""
        try:
            return self.hasher.verify(password_hash, password)
        except (VerifyMismatchError, Exception):
            return False

    def create_token(
        self,
        user_id: str,
        tenant_id: str,
        role: str,
        clinic_id: str = "clinic-main",
        custom_scopes: Optional[List[str]] = None,
    ) -> str:
        """Generate a signed JWT token containing institutional context."""
        now = int(time.time())
        scopes = custom_scopes if custom_scopes is not None else ROLE_SCOPES.get(role, [])
        payload = {
            "sub": user_id,
            "tenant_id": tenant_id,
            "clinic_id": clinic_id,
            "role": role,
            "scopes": scopes,
            "iat": now,
            "exp": now + self.token_expire_seconds,
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def register_api_key(self, api_key: str, user: AuthenticatedUser) -> None:
        """Register an API key for a tenant actor."""
        self._api_keys[api_key] = user

    async def validate_token(self, token: str) -> Optional[AuthenticatedUser]:
        """Validate JWT session token and extract authenticated user context."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id = payload.get("sub")
            tenant_id = payload.get("tenant_id")
            clinic_id = payload.get("clinic_id", "clinic-main")
            role = payload.get("role", "clinician")
            scopes = payload.get("scopes", ROLE_SCOPES.get(role, []))

            if not user_id or not tenant_id:
                return None

            return AuthenticatedUser(
                user_id=user_id,
                tenant_id=tenant_id,
                clinic_id=clinic_id,
                role=role,
                scopes=scopes,
            )
        except JWTError:
            return None

    async def validate_api_key(self, api_key: str) -> Optional[AuthenticatedUser]:
        """Validate API key and return authenticated tenant context."""
        return self._api_keys.get(api_key)

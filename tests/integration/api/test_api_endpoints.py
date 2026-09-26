"""Integration tests for FastAPI REST and SSE endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient
from medrag.interfaces.api.app import app
from medrag.interfaces.api.dependencies import get_services


@pytest.fixture
def auth_tokens():
    services = get_services()
    clinician_token = services.auth_provider.create_token(
        user_id="usr-dr-jones",
        tenant_id="tenant-st-jude",
        role="clinician",
    )
    cmo_token = services.auth_provider.create_token(
        user_id="usr-cmo-watson",
        tenant_id="tenant-st-jude",
        role="cmo",
    )
    admin_token = services.auth_provider.create_token(
        user_id="usr-admin-sys",
        tenant_id="tenant-st-jude",
        role="admin",
    )
    other_tenant_token = services.auth_provider.create_token(
        user_id="usr-dr-other",
        tenant_id="tenant-other-clinic",
        role="clinician",
    )
    return {
        "clinician": clinician_token,
        "cmo": cmo_token,
        "admin": admin_token,
        "other_tenant": other_tenant_token,
    }


@pytest.mark.asyncio
async def test_health_check_unauthenticated():
    """Health check endpoint is public and reports all subsystems healthy."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["subsystems"]["lancedb"] == "healthy"


@pytest.mark.asyncio
async def test_root_clinician_workspace_ui_served():
    """Root endpoint / serves the institutional Clinician Workspace HTML."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert "MedRAG" in response.text
        assert "Patient Explorer" in response.text


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected():
    """Protected endpoints reject requests without token or API key with 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/patients")
        assert response.status_code == 401
        data = response.json()
        assert data["error_code"] == "UNAUTHENTICATED"


@pytest.mark.asyncio
async def test_scope_enforcement_clinician_cannot_read_audit_log(auth_tokens):
    """Clinician lacking 'audit:read' receives HTTP 403 on audit logs."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/audit/log",
            headers={"Authorization": f"Bearer {auth_tokens['clinician']}"},
        )
        assert response.status_code == 403
        data = response.json()
        assert data["error_code"] == "INSUFFICIENT_SCOPE"


@pytest.mark.asyncio
async def test_cmo_can_read_audit_log(auth_tokens):
    """CMO possesses 'audit:read' scope and successfully accesses audit log."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/audit/log",
            headers={"Authorization": f"Bearer {auth_tokens['cmo']}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


@pytest.mark.asyncio
async def test_fhir_bundle_ingest_enqueue(auth_tokens):
    """Uploading FHIR R4 Bundle enqueues background ingestion job."""
    fhir_bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "pat-api-001",
                }
            }
        ],
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/patients/ingest/fhir",
            json=fhir_bundle,
            headers={"Authorization": f"Bearer {auth_tokens['clinician']}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["patient_id"] == "pat-api-001"
        assert data["status"] == "queued"
        assert "job_id" in data


@pytest.mark.asyncio
async def test_clinical_query_non_streaming(auth_tokens):
    """Non-streaming clinical query returns verified report with footnotes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/clinical/query",
            json={
                "query_text": "Assess guideline therapy for heart failure",
                "stream": False,
            },
            headers={"Authorization": f"Bearer {auth_tokens['clinician']}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "report" in data
        assert "raw_synthesis" in data["report"]
        assert "verified_footnotes" in data["report"]


@pytest.mark.asyncio
async def test_clinical_query_sse_streaming(auth_tokens):
    """Clinical query with stream=True returns Server-Sent Events stream."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/clinical/query",
            json={
                "query_text": "Evaluate renal management",
                "stream": True,
            },
            headers={"Authorization": f"Bearer {auth_tokens['clinician']}"},
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        body_text = response.text
        assert "event: synthesis_chunk" in body_text
        assert "event: synthesis_complete" in body_text


@pytest.mark.asyncio
async def test_rate_limiter_quota_breach(auth_tokens):
    """Breaching request rate limit raises HTTP 429 QuotaExceededException."""
    services = get_services()
    # Configure tiny rate limit
    services.rate_limiter.set_tenant_tier("tenant-st-jude", "community")
    # Artificially fill quota
    for _ in range(10):
        services.rate_limiter._request_timestamps["tenant-st-jude"].append(9999999999.0)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/clinical/query",
            json={
                "query_text": "Test quota limit breach",
                "stream": False,
            },
            headers={"Authorization": f"Bearer {auth_tokens['clinician']}"},
        )
        assert response.status_code == 429
        data = response.json()
        assert data["error_code"] == "QUOTA_EXCEEDED"

    # Reset limiter for other tests
    services.rate_limiter._request_timestamps["tenant-st-jude"].clear()

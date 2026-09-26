# MedRAG v2.0 - Multi-Stage Institutional Production Container
# Stage 1: Build & Dependency Resolution
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip setuptools wheel && \
    /opt/venv/bin/pip install --no-cache-dir .

# Stage 2: Minimal Distroless / Hardened Runtime
FROM python:3.12-slim AS runtime

LABEL maintainer="MedRAG Core Architecture Team"
LABEL version="2.0.0"
LABEL description="Institutional-Grade Clinical AI Intelligence SaaS Platform"

WORKDIR /app

# Create non-root institutional service user (UID 10001)
RUN groupadd -g 10001 medrag && \
    useradd -u 10001 -g medrag -s /bin/bash -m medrag && \
    mkdir -p /app/data /app/logs && \
    chown -R medrag:medrag /app

# Copy virtual environment and source code
COPY --from=builder /opt/venv /opt/venv
COPY --chown=medrag:medrag src/ /app/src/
COPY --chown=medrag:medrag scripts/ /app/scripts/

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    MEDRAG_DATA_DIR=/app/data \
    MEDRAG_LOG_LEVEL=INFO

USER medrag

EXPOSE 8000

# Docker Healthcheck verifying /api/v1/health
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=3)" || exit 1

ENTRYPOINT ["uvicorn", "medrag.interfaces.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

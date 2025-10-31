# Multi-stage build for the Tiger REST API service
FROM python:3.11-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

WORKDIR /workspace

COPY pyproject.toml uv.lock ./
COPY packages/shared/pyproject.toml packages/shared/
COPY packages/shared/src/ packages/shared/src/

RUN uv sync --frozen --no-dev

FROM python:3.11-slim AS production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/workspace/.venv/bin:$PATH" \
    LOG_LEVEL=info

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

RUN groupadd -r tiger && useradd -r -g tiger tiger

WORKDIR /app

COPY --from=builder /workspace/.venv /workspace/.venv

COPY tiger_rest_api_full.py ./
COPY references/openapi-python-sdk/tigeropen/ ./tigeropen/

RUN mkdir -p /app/logs && \
    chown -R tiger:tiger /app

USER tiger

EXPOSE 9000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:9000/health || exit 1

CMD ["python", "tiger_rest_api_full.py"]

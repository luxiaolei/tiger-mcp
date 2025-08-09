# Multi-stage build for Dashboard API
FROM python:3.11-slim as builder

# Set environment variables for build
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install UV for package management
RUN pip install uv

# Set working directory
WORKDIR /workspace

# Copy workspace files
COPY pyproject.toml uv.lock ./
COPY packages/dashboard-api/pyproject.toml packages/dashboard-api/
COPY packages/shared/pyproject.toml packages/shared/
COPY packages/database/pyproject.toml packages/database/
COPY packages/shared/src/ packages/shared/src/
COPY packages/database/src/ packages/database/src/

# Install dependencies using UV
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/workspace/.venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r tiger && useradd -r -g tiger tiger

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /workspace/.venv /workspace/.venv

# Copy source code
COPY packages/dashboard-api/src/ ./
COPY packages/shared/src/ ./
COPY packages/database/src/ ./

# Create necessary directories and set permissions
RUN mkdir -p /app/logs && \
    chown -R tiger:tiger /app

# Switch to non-root user
USER tiger

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Expose port
EXPOSE 8001

# Default command
CMD ["uvicorn", "dashboard_api.main:app", "--host", "0.0.0.0", "--port", "8001"]
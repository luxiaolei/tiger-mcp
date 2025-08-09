# Multi-stage build for Database migrations and utilities
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
COPY packages/database/pyproject.toml packages/database/
COPY packages/shared/pyproject.toml packages/shared/
COPY packages/shared/src/ packages/shared/src/

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
    postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r tiger && useradd -r -g tiger tiger

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /workspace/.venv /workspace/.venv

# Copy source code and configuration
COPY packages/database/src/ ./
COPY packages/shared/src/ ./
COPY packages/database/alembic.ini ./
COPY packages/database/manage_db.py ./

# Create necessary directories and set permissions
RUN mkdir -p /app/logs && \
    chown -R tiger:tiger /app

# Switch to non-root user
USER tiger

# Default command (for database initialization/migration)
CMD ["python", "manage_db.py", "upgrade"]
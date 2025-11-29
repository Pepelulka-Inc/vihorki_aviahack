# Multi-stage Dockerfile for vihorki service
# Stage 1: Builder
FROM python:3.12-alpine AS builder

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    postgresql-dev \
    cargo \
    rust

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /uvx /bin/

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Stage 2: Runtime
FROM python:3.12-alpine

# Install runtime dependencies only
RUN apk add --no-cache \
    libpq \
    libffi

# Copy uv from builder
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /uvx /bin/

WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /app/.venv /app/.venv

# Copy source code
COPY . .

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 9002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:9002/health')" || exit 1

# Run using uv
CMD ["uv", "run", "python", "main.py"]
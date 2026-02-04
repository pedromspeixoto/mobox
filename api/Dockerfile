# Multi-stage build for FastAPI backend
# Build context: project root (.)
FROM python:3.12-slim as builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory (api package)
WORKDIR /app/api

# Copy api and shared package (shared is a path dependency)
COPY api/ ./
COPY shared /app/shared

# Install dependencies
RUN uv sync --frozen

# Final stage
FROM python:3.12-slim

# Install uv and curl (for healthcheck)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app/api

# Copy virtual environment from builder
COPY --from=builder /app/api/.venv /app/api/.venv

# Copy project files
COPY api/ ./
COPY shared /app/shared

# Set environment variables
ENV PATH="/app/api/.venv/bin:$PATH"
ENV PYTHONPATH="/app/api:$PYTHONPATH"

# Expose FastAPI port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8080/api/v1/health || exit 1

# Run migrations and start FastAPI with uvicorn
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn main:app --host 0.0.0.0 --port 8080"]

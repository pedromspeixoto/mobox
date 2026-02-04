# Multi-stage build for Dagster deployment
FROM python:3.11-slim as builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies (including dev dependencies for dagster-webserver)
RUN uv sync --frozen

# Final stage
FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY features/ ./features/
COPY workspace.yaml ./

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src:$PYTHONPATH"
ENV DAGSTER_HOME=/app/.dagster_home

# Create dagster home directory
RUN mkdir -p /app/.dagster_home

# Expose Dagster webserver port
EXPOSE 3000

# Default command (can be overridden in docker-compose)
# dagster dev runs both webserver and daemon together
CMD ["dagster", "dev", "-h", "0.0.0.0", "-p", "3000", "-w", "workspace.yaml"]

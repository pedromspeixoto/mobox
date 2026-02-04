# Deepagents Simple Research Agent - Sandbox Container
# Build from agents/ directory: docker build -f deepagents-simple-research/Dockerfile -t deepagents-simple-research .

# ============================================
# Stage 1: Builder - Install dependencies with uv
# ============================================
FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set uv environment variables for optimal caching
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=python3.12

# Use /build to mirror agents/ directory structure (for relative path ../shared)
WORKDIR /build

# Copy shared package (at project root)
COPY shared/ ./shared/

# Copy agent directory with dependency files first for layer caching
COPY agents/deepagents-simple-research/pyproject.toml agents/deepagents-simple-research/uv.lock ./deepagents-simple-research/

# Install dependencies (--no-editable ensures packages are copied, not linked)
WORKDIR /build/deepagents-simple-research
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev --no-editable

# Copy agent source code
COPY agents/deepagents-simple-research/run_agent.py ./
COPY agents/deepagents-simple-research/tools/ ./tools/
COPY agents/deepagents-simple-research/prompts/ ./prompts/

# Install the project (--no-editable for portable venv)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# ============================================
# Stage 2: Runtime - Minimal final image
# ============================================
FROM python:3.12-slim AS runtime

# Install only runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security (optional, comment out if Modal requires root)
# RUN useradd --create-home --shell /bin/bash agent
# USER agent

WORKDIR /workspace

# Copy the virtual environment from builder
COPY --from=builder /build/deepagents-simple-research/.venv /app/.venv

# Copy application code
COPY --from=builder /build/deepagents-simple-research/run_agent.py /app/
COPY --from=builder /build/deepagents-simple-research/tools/ /app/tools/
COPY --from=builder /build/deepagents-simple-research/prompts/ /app/prompts/

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# No ENTRYPOINT - Modal will specify the full command

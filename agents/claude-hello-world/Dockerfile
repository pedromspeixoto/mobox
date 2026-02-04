# Hello World Agent - Sandbox Container
# Build from agents/ directory: docker build -f claude-hello-world/Dockerfile -t claude-hello-world .

# ============================================
# Stage 1: Builder - Install Python deps with uv
# ============================================
FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set uv environment variables
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=python3.12

# Mirror agents/ directory structure for relative path ../shared
WORKDIR /build

# Copy shared package (at project root)
COPY shared/ ./shared/

# Copy dependency files first for layer caching
COPY agents/claude-hello-world/pyproject.toml agents/claude-hello-world/uv.lock ./claude-hello-world/

# Install dependencies (--no-editable ensures packages are copied, not linked)
WORKDIR /build/claude-hello-world
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev --no-editable

# Copy agent source
COPY agents/claude-hello-world/run_agent.py ./

# Install the project (--no-editable for portable venv)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# ============================================
# Stage 2: Runtime - Minimal final image
# ============================================
FROM python:3.12-slim AS runtime

# Install system dependencies + Node.js in single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    ca-certificates \
    gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @anthropic-ai/claude-code \
    && npm cache clean --force \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /workspace

# Copy virtual environment from builder
COPY --from=builder /build/claude-hello-world/.venv /app/.venv

# Copy agent code
COPY --from=builder /build/claude-hello-world/run_agent.py /app/

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# No ENTRYPOINT - Modal will specify the full command

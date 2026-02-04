# DeepAgents Multi-Hop RAG Agent - Mobox Sandbox Container
#
# Purpose: Multi-hop RAG agent using Weaviate vector store. Executed by Mobox API
# with entrypoint: python /app/run_agent.py
#
# Build from mobox root:  make deepagents-multi-hop-rag
# Build from agents/:     docker build -f deepagents-multi-hop-rag/Dockerfile -t deepagents-multi-hop-rag .

# ============================================
# Stage 1: Builder - Install dependencies with uv
# ============================================
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=python3.12

# Mirror structure for shared package (../../shared from agent dir)
WORKDIR /build
COPY shared/ ./shared/
COPY agents/deepagents-multi-hop-rag/pyproject.toml agents/deepagents-multi-hop-rag/uv.lock ./deepagents-multi-hop-rag/

WORKDIR /build/deepagents-multi-hop-rag
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev --no-editable

COPY agents/deepagents-multi-hop-rag/run_agent.py ./
COPY agents/deepagents-multi-hop-rag/tools/ ./tools/
COPY agents/deepagents-multi-hop-rag/prompts/ ./prompts/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# ============================================
# Stage 2: Runtime - Minimal image for Mobox sandbox
# ============================================
FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /workspace

COPY --from=builder /build/deepagents-multi-hop-rag/.venv /app/.venv
COPY --from=builder /build/deepagents-multi-hop-rag/run_agent.py /app/
COPY --from=builder /build/deepagents-multi-hop-rag/tools/ /app/tools/
COPY --from=builder /build/deepagents-multi-hop-rag/prompts/ /app/prompts/

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Entrypoint set by Mobox API per agent.yaml
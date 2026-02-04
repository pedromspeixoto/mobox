# Makefile for Mobox Agent Docker Images

REGISTRY ?=
TAG ?= latest

# Add registry prefix if set
ifdef REGISTRY
  IMAGE_PREFIX := $(REGISTRY)/
else
  IMAGE_PREFIX :=
endif

.PHONY: help build-all sync-agents \
        deepagents-simple-research deepagents-simple-research-linux \
        deepagents-multi-hop-rag deepagents-multi-hop-rag-linux \
        claude-hello-world claude-hello-world-linux \
        claude-research claude-research-linux

help:
	@echo "Mobox Agent Build Commands"
	@echo ""
	@echo "Build for current platform:"
	@echo "  make deepagents-simple-research"
	@echo "  make deepagents-multi-hop-rag"
	@echo "  make claude-hello-world"
	@echo "  make claude-research"
	@echo "  make build-all"
	@echo ""
	@echo "Build for Linux (amd64):"
	@echo "  make deepagents-simple-research-linux"
	@echo "  make deepagents-multi-hop-rag-linux"
	@echo "  make claude-hello-world-linux"
	@echo "  make claude-research-linux"
	@echo ""
	@echo "Variables:"
	@echo "  REGISTRY=docker.io/myuser    # Registry prefix"
	@echo "  TAG=v1.0.0                   # Image tag (default: latest)"
	@echo ""
	@echo "Examples:"
	@echo "  make deepagents-simple-research TAG=v1.0.0"
	@echo "  make claude-research-linux REGISTRY=docker.io/myuser TAG=v2.0.0"
	@echo ""
	@echo "Local development (subprocess sandbox):"
	@echo "  make sync-agents    # Sync shared package in all agents (run after pulling shared changes)"

# Sync shared package in agents that use it (for local subprocess runs)
sync-agents:
	cd agents/deepagents-simple-research && uv sync --reinstall-package shared
	cd agents/deepagents-multi-hop-rag && uv sync --reinstall-package shared
	cd agents/claude-hello-world && uv sync --reinstall-package shared
	cd agents/claude-research && uv sync --reinstall-package shared

# Build all agents
build-all: deepagents-simple-research deepagents-multi-hop-rag claude-hello-world claude-research

# ============================================
# deepagents-simple-research
# ============================================
deepagents-simple-research:
	docker build -f agents/deepagents-simple-research/Dockerfile \
		-t $(IMAGE_PREFIX)deepagents-simple-research:$(TAG) .

deepagents-simple-research-linux:
	docker build -f agents/deepagents-simple-research/Dockerfile \
		--platform linux/amd64 \
		-t $(IMAGE_PREFIX)deepagents-simple-research:$(TAG) .

# ============================================
# deepagents-multi-hop-rag
# ============================================
deepagents-multi-hop-rag:
	docker build -f agents/deepagents-multi-hop-rag/Dockerfile \
		-t $(IMAGE_PREFIX)deepagents-multi-hop-rag:$(TAG) .

deepagents-multi-hop-rag-linux:
	docker build -f agents/deepagents-multi-hop-rag/Dockerfile \
		--platform linux/amd64 \
		-t $(IMAGE_PREFIX)deepagents-multi-hop-rag:$(TAG) .

# ============================================
# claude-hello-world
# ============================================
claude-hello-world:
	docker build -f agents/claude-hello-world/Dockerfile \
		-t $(IMAGE_PREFIX)claude-hello-world:$(TAG) .

claude-hello-world-linux:
	docker build -f agents/claude-hello-world/Dockerfile \
		--platform linux/amd64 \
		-t $(IMAGE_PREFIX)claude-hello-world:$(TAG) .

# ============================================
# claude-research
# ============================================
claude-research:
	docker build -f agents/claude-research/Dockerfile \
		-t $(IMAGE_PREFIX)claude-research:$(TAG) .

claude-research-linux:
	docker build -f agents/claude-research/Dockerfile \
		--platform linux/amd64 \
		-t $(IMAGE_PREFIX)claude-research:$(TAG) .

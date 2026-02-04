# Agents

Agent implementations for Mobox.

## Structure

```
mobox/
└── agents/
   ├── claude-hello-world/      # Simple Claude SDK demo
   ├── claude-research/         # Multi-agent research with PDF/PPTX
   └── deepagents-simple-research/  # LangChain DeepAgents orchestrator
```

## Building Docker Images

From repo root (`mobox/`):

```bash
# Build for current platform
make deepagents-simple-research
make claude-hello-world
make claude-research
make build-all

# Build for Linux (amd64)
make deepagents-simple-research-linux
make claude-hello-world-linux
make claude-research-linux

# With custom tag
make deepagents-simple-research TAG=v1.0.0

# With registry prefix
make deepagents-simple-research REGISTRY=docker.io/myuser TAG=v1.0.0
```
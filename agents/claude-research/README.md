# Claude Research Agent

A research agent that uses Claude Agent SDK to perform deep research tasks.

## Local Development

```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY

# Run with uv
uv run run_agent.py --prompt "Research the latest trends in AI"

# Or read prompt from stdin
echo "Research the latest trends in AI" | uv run run_agent.py --stdin
```

## Output Format

The agent streams JSON events to stdout:
- `start` - Agent started
- `text` - Text response from Claude
- `tool_use` - Tool execution (Read, Write, Bash, etc.)
- `result` - Final result with stats
- `error` - Error occurred
- `done` - Agent finished

## Docker

```bash
docker build -t claude-research .
docker run -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY claude-research --prompt "Research the latest trends in AI"
```

# rfd-blog-engine

MCP server for blog post generation and publishing to WordPress and Dev.to.

## Overview

A self-contained Python MCP server that generates, stores, approves, and publishes blog posts. Runs on Nitro via stdio transport for Claude Desktop. Designed to fold into PrivyBot Phase 31 later via SSE transport on Tower.

## Installation

```bash
uv sync
```

## Configuration

Copy `.env.example` to `.env` and fill in credentials:

```bash
cp .env.example .env
```

Required credentials:
- WordPress: `WP_URL`, `WP_USER`, `WP_APP_PASSWORD`
- Dev.to: `DEVTO_API_KEY`
- Model router: `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `OLLAMA_MODEL`

## Usage

### Running the MCP server

```bash
uv run python -m blog_engine.server
```

### Claude Desktop configuration

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "rfd-blog-engine": {
      "command": "uv",
      "args": ["run", "python", "-m", "blog_engine.server"],
      "cwd": "C:/Github/rfd-blog-engine"
    }
  }
}
```

## Development

### Running tests

```bash
uv run pytest tests/ -v
```

### Project structure

```
rfd-blog-engine/
├── blog_engine/
│   ├── infra/          # Database, caching, model routing, logging
│   ├── api/            # WordPress and Dev.to handlers
│   ├── core/           # Inventory, drafts, generation, publishing
│   └── tools/          # MCP tools exposed to Claude
├── data/
│   ├── inventory.yaml  # Post inventory
│   └── drafts/         # JSON draft files
├── tests/              # Test suite
└── docs/               # SDD and ADRs
```

## Documentation

See `docs/rfd_blog_engine_SDD_v0_2.md` for the complete Software Design Document.

## License

RFD IT Services Ltd. — Private project.

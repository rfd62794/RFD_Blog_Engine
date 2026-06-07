# rfd-blog-engine — SDD v0.1

*June 2026 | RFD IT Services Ltd.*
*Director: Claude | Agent: Windsurf/Antigravity | Methodology: Spec-Driven Development*

---

## §0 — Project Overview

**What it is:**
A self-contained Python MCP server that generates, stores, approves, and publishes blog posts to WordPress and Dev.to. Runs on Nitro (laptop) via stdio transport. Folds into PrivyBot Phase 31 later via SSE transport on Tower.

**Why it exists:**
PrivyBot can draft blog posts to Telegram. It cannot publish them. WordPress and Dev.to tools have been declared twice (Phase 31 scope, Phase 16 directive) and never built. This project builds those tools as a standalone unit — usable now via Claude Desktop MCP, absorbable into PrivyBot later without migration.

**What it is not:**
- Not a replacement for PrivyBot's publishing layer
- Not a CMS or full content management system
- Not a scheduling system (deferred)
- Not a voice memo pipeline (deferred)
- Not a GA4, Hashnode, or third-platform tool (deferred)

---

## §1 — Tech Stack

| Layer | Technology | Source |
|---|---|---|
| Language | Python 3.12 | Standard |
| MCP transport | FastMCP (stdio) | RFD_Sheets_MCP pattern |
| WordPress API | httpx + WP REST API v2 | New |
| Dev.to API | httpx + Dev.to REST API | New |
| Draft storage | JSON files | New |
| Context/memory | SQLite (WAL mode) | PrivyBot DBManager pattern |
| Model routing | Groq → Gemini → OpenRouter → Ollama | PrivyBot model_router.py |
| Base API handler | BaseAPIHandler | PrivyBot infra/base_api_handler.py |
| Config | python-dotenv (.env) | Standard |
| CLI | Click | OpenAgent pattern |
| Testing | pytest + pytest-asyncio | Standard |
| Dependency mgmt | uv | Tower standard |

**Borrowed directly from existing repos on Nitro:**

| File | Source repo | What it provides |
|---|---|---|
| `base_api_handler.py` | PrivyBot `infra/` | HTTP client base, retry, rate limit |
| `db_manager.py` | PrivyBot `infra/` | SQLite WAL, exponential backoff |
| `model_router.py` | PrivyBot `infra/` | Groq → Gemini → OpenRouter → Ollama |
| `cache_manager.py` | PrivyBot `infra/` | TTL cache, stale fallback |
| FastMCP server setup | RFD_Sheets_MCP | stdio transport pattern |
| CLI entry point | OpenAgent | Click structure |
| YAML inventory schema | ContentPipeline | Post inventory format |

> ⚠️ Borrowed files are copied, not symlinked. They diverge independently from source repos.

---

## §2 — Architecture

### Directory Structure

```
rfd-blog-engine/
├── .env                          # credentials, never committed
├── .env.example                  # template, committed
├── pyproject.toml
├── README.md
├── docs/
│   ├── adr/
│   │   ├── ADR-001.md            # JSON for drafts, SQLite for context
│   │   ├── ADR-002.md            # Always draft first, approval required
│   │   ├── ADR-003.md            # stdio transport, SSE deferred
│   │   ├── ADR-004.md            # Model routing hierarchy
│   │   └── ADR-005.md            # Inventory schema ownership
│   └── state/
│       └── current.md
├── data/
│   ├── inventory.yaml            # 70-post inventory
│   └── drafts/                   # JSON draft files, one per post
├── blog_engine/
│   ├── __init__.py
│   ├── server.py                 # FastMCP server, tool registration
│   ├── cli.py                    # Click CLI entry point
│   ├── infra/
│   │   ├── __init__.py
│   │   ├── base_api_handler.py   # Borrowed from PrivyBot
│   │   ├── db_manager.py         # Borrowed from PrivyBot
│   │   ├── cache_manager.py      # Borrowed from PrivyBot
│   │   └── model_router.py       # Borrowed from PrivyBot
│   ├── api/
│   │   ├── __init__.py
│   │   ├── wordpress.py          # WP REST API handler
│   │   └── devto.py              # Dev.to REST API handler
│   ├── core/
│   │   ├── __init__.py
│   │   ├── inventory.py          # YAML inventory reader/writer
│   │   ├── draft_manager.py      # JSON draft CRUD + SQLite context
│   │   ├── generator.py          # Internal generation via model router
│   │   └── publisher.py          # Orchestrates approve → WP → Dev.to
│   └── tools/
│       ├── __init__.py
│       ├── generate_tools.py     # MCP tools: generate, get_context
│       ├── draft_tools.py        # MCP tools: list, get, update, approve
│       └── publish_tools.py      # MCP tools: publish_wp, publish_devto
└── tests/
    ├── conftest.py
    ├── test_inventory.py
    ├── test_draft_manager.py
    ├── test_generator.py
    ├── test_wordpress.py
    ├── test_devto.py
    └── test_publisher.py
```

---

### Data Flow

**Internal generation path:**
```
list_inventory() → pick post_id
→ get_post_context(post_id) → loads inventory notes + frame template
→ generate_post(post_id) → model_router → draft JSON saved
→ get_draft(post_id) → review in Claude
→ approve_draft(post_id) → status: approved
→ publish_to_wordpress(post_id) → WP draft created, URL returned
→ publish_to_devto(post_id) → Dev.to draft, canonical = WP URL
```

**External generation path (Claude browser session):**
```
Claude drafts post content in conversation
→ create_draft(post_id, title, content) → draft JSON saved
→ approve_draft(post_id)
→ publish_to_wordpress(post_id)
→ publish_to_devto(post_id)
```

Both paths converge at the same draft JSON. The publisher doesn't know or care how the draft was generated.

---

### Draft JSON Schema

```json
{
  "post_id": "dev-001",
  "title": "I built the same game for 20 years without knowing it",
  "status": "draft",
  "content": "...",
  "excerpt": "...",
  "tags": ["identity", "voiddrift", "origin"],
  "categories": ["developer-identity"],
  "tags_source": "auto",
  "categories_source": "manual",
  "created_at": "2026-06-07T11:00:00",
  "updated_at": "2026-06-07T11:00:00",
  "approved_at": null,
  "approved_by": null,
  "wp_post_id": null,
  "wp_url": null,
  "devto_id": null,
  "devto_url": null,
  "published_at": null,
  "revision_count": 0,
  "generation_source": "internal"
}
```

`tags_source` and `categories_source`: `"auto"` | `"manual"` | `"per_post"` — tracks how they were assigned.

---

### SQLite Context Schema

```sql
-- Post thread relationships
CREATE TABLE post_threads (
    id INTEGER PRIMARY KEY,
    thread_name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE post_thread_members (
    post_id TEXT NOT NULL,
    thread_id INTEGER NOT NULL,
    sequence INTEGER,
    FOREIGN KEY (thread_id) REFERENCES post_threads(id)
);

-- Post context memory
CREATE TABLE post_context (
    post_id TEXT PRIMARY KEY,
    raw_extraction TEXT,        -- raw Q&A answers from extraction session
    frame_moment TEXT,          -- MOMENT slot
    frame_surprise TEXT,        -- SURPRISE slot
    frame_struggle TEXT,        -- STRUGGLE slot
    frame_lesson TEXT,          -- LESSON slot
    frame_next TEXT,            -- NEXT slot
    related_posts TEXT,         -- JSON array of related post_ids
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Draft revision history
CREATE TABLE draft_revisions (
    id INTEGER PRIMARY KEY,
    post_id TEXT NOT NULL,
    revision_number INTEGER NOT NULL,
    content TEXT NOT NULL,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    saved_by TEXT
);

-- Publish log
CREATE TABLE publish_log (
    id INTEGER PRIMARY KEY,
    post_id TEXT NOT NULL,
    platform TEXT NOT NULL,     -- wordpress | devto
    status TEXT NOT NULL,       -- success | failed
    response_data TEXT,         -- JSON
    published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### MCP Tool Surface (exposed to Claude)

| Tool | Description |
|---|---|
| `list_inventory` | Returns pending/drafted/approved/published posts |
| `get_post_context` | Returns inventory notes + frame slots for a post_id |
| `generate_post` | Internal generation via model router → saves draft |
| `create_draft` | External: saves Claude-authored content as draft |
| `get_draft` | Returns current draft content for review |
| `update_draft` | Updates draft content, increments revision count |
| `approve_draft` | Sets approved status, records approver |
| `publish_to_wordpress` | Pushes approved draft to WP, returns URL |
| `publish_to_devto` | Pushes to Dev.to with canonical WP URL |
| `get_publish_status` | Returns full status for a post_id |
| `list_threads` | Returns all post thread groups |
| `add_to_thread` | Adds post to a named thread |

---

## §3 — Architecture Decision Records

### ADR-001: JSON for drafts, SQLite for context

**Status:** Accepted

**Context:** Need persistent storage for draft state and post relationships. Two different access patterns — drafts are read/written as whole documents, context is queried relationally.

**Decision:** JSON files for draft state (one file per post, named by post_id). SQLite WAL for context memory, revision history, thread relationships, and publish log.

**Consequences:** Drafts are human-readable and portable. Context is queryable and connects to PrivyBot memory system later. Draft files can be committed to git as a snapshot. SQLite never committed.

---

### ADR-002: Always draft first, approval required before publish

**Status:** Accepted

**Context:** Publishing errors are hard to reverse. WordPress posts can be deleted but Dev.to syndication with canonical URL affects SEO immediately.

**Decision:** All generation produces a draft JSON with `status: draft`. Publish tools check for `status: approved` before executing. No publish path bypasses the approval gate. Approver field records who approved (human, claude, or agent name).

**Consequences:** Nothing publishes without explicit approval. Future review agent can set approver field automatically. Human approval remains the default for MVP.

---

### ADR-003: stdio transport now, SSE deferred

**Status:** Accepted

**Context:** Claude Desktop uses stdio MCP transport. Tower uses SSE via mcp-proxy. Building for both simultaneously adds complexity with no immediate benefit.

**Decision:** FastMCP stdio only for MVP. When absorbed into PrivyBot, transport switches to SSE. The tool layer is transport-agnostic — only `server.py` changes.

**Consequences:** Claude Desktop can use it immediately on Nitro. Tower deployment requires one server.py rewrite, no tool changes.

---

### ADR-004: Model routing hierarchy

**Status:** Accepted

**Context:** Internal generation needs a model. External API costs money. Need fallback chain.

**Decision:** Groq (free, fast) → Gemini Direct → OpenRouter → Ollama (local, last resort). Same hierarchy as PrivyBot. Model router borrowed directly from PrivyBot infra/.

**Consequences:** Generation is free-tier first. Cost only incurred if Groq is unavailable. Ollama on Nitro handles offline sessions.

---

### ADR-005: Inventory schema ownership

**Status:** Accepted

**Context:** 70-post inventory exists in this session as context. PrivyBot and ContentPipeline may eventually share it. Need a schema that doesn't require migration when shared.

**Decision:** `data/inventory.yaml` is owned by rfd-blog-engine for MVP. Schema is designed to be readable by other tools without modification. Status field (`pending | drafted | approved | published`) is the only field this tool writes. All other fields are read-only from other tools' perspective.

**Consequences:** Inventory can be symlinked or copied to other repos later. Status updates are safe to merge. No circular dependency on PrivyBot.

---

## §4 — Phase Roadmap

### Phase 1 — Foundation
New repo, directory structure, borrowed infra files, pyproject.toml, .env setup, inventory.yaml seeded with 70 posts, SQLite schema initialized, pytest passing.

**Target floor: 0 → 15**

### Phase 2 — Draft Manager
JSON draft CRUD, SQLite context tables, revision history, draft_manager.py complete with tests.

**Target floor: 15 → 30**

### Phase 3 — API Handlers
wordpress.py and devto.py handlers, all external calls mocked in tests, canonical URL enforcement.

**Target floor: 30 → 45**

### Phase 4 — Generator
Internal generation via model_router, RFD Content Frame prompt, frame slot extraction from inventory context.

**Target floor: 45 → 55**

### Phase 5 — MCP Server + Tools
FastMCP server, all 12 tools registered and callable from Claude Desktop, stdio transport verified.

**Target floor: 55 → 70**

### Phase 6 — Publisher + Approval Gate
Full publish flow: approve → WordPress → Dev.to → status update. Publish log written. Error handling: WP fail aborts, Dev.to fail logs but does not roll back WP.

**Target floor: 70 → 85**

### Phase 7 — Integration Verification
Full end-to-end test: generate → draft → approve → publish to WP staging → Dev.to draft. Manual verification with real credentials. Claude Desktop MCP connection confirmed.

**Target floor: 85 → 85** (no new tests, all manual)

---

## §5 — Deferred (Not in Scope)

- Voice memo transcription input
- GA4 read access
- Hashnode syndication
- LinkedIn, Reddit, Patreon distribution
- Scheduling system for future-dated posts
- Review agent (automated approval)
- Gumroad integration
- Tower / PrivyBot absorption (Phase 31)
- n8n integration
- Multi-author support

---

## §6 — Credentials Required

| Credential | How to get | .env key |
|---|---|---|
| WordPress Application Password | WP Admin → Users → Profile → Application Passwords | `WP_URL`, `WP_USER`, `WP_APP_PASSWORD` |
| Dev.to API Key | dev.to/settings/extensions | `DEVTO_API_KEY` |
| Groq API Key | console.groq.com | `GROQ_API_KEY` |
| Gemini API Key | aistudio.google.com | `GEMINI_API_KEY` |
| OpenRouter API Key | openrouter.ai | `OPENROUTER_API_KEY` |

Groq, Gemini, OpenRouter keys likely already in Nitro .env from PrivyBot. Copy them.

---

## §7 — State File

`docs/state/current.md` initialized at project creation:

```markdown
phase: 'Phase 1 — Foundation'
certified_floor: 0/0/0
what_is_next: 'Phase 2 — Draft Manager'
```

---

*rfd-blog-engine SDD v0.1 | June 2026 | RFD IT Services Ltd.*
*Director → Pipeline → Agent. Spec first. Test floor always real.*

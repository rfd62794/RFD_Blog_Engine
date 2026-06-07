# rfd-blog-engine — SDD v0.2

*June 2026 | RFD IT Services Ltd.*
*Director: Claude | Agent: Windsurf/Antigravity | Methodology: Spec-Driven Development*
*Supersedes: SDD v0.1*

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
- Not a multi-writer concurrent system (single-writer model, see ADR-008)

---

## §1 — Tech Stack

| Layer | Technology | Source |
|---|---|---|
| Language | Python 3.12 | Standard |
| MCP transport | FastMCP (stdio) | RFD_Sheets_MCP pattern |
| WordPress API | httpx + WP REST API v2 | New |
| Dev.to API | httpx + Dev.to REST API | New |
| Draft storage | JSON files (single-writer) | New |
| Context/memory | SQLite (WAL mode) | PrivyBot DBManager pattern |
| Model routing | Groq → Gemini → OpenRouter → Ollama | PrivyBot model_router.py |
| Base API handler | BaseAPIHandler | PrivyBot infra/base_api_handler.py |
| Config | python-dotenv (.env) | Standard |
| CLI | Click | OpenAgent pattern |
| Testing | pytest + pytest-asyncio | Standard |
| Dependency mgmt | uv | Tower standard |
| Logging | structlog (JSON structured) | New |

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

> ⚠️ Borrowed files are **copied, not symlinked**. They diverge permanently from source repos. Bug fixes in PrivyBot do not automatically apply here. This is intentional — the repos are independent. If a critical fix is needed, it is applied manually to both.

**Environment variable alignment:**
PrivyBot and rfd-blog-engine use identical environment variable names for shared credentials: `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `OLLAMA_MODEL`. Copy directly from Nitro PrivyBot `.env`. No renaming required.

---

## §2 — Architecture

### Directory Structure

```
rfd-blog-engine/
├── .env                          # credentials, never committed
├── .env.example                  # template, committed
├── pyproject.toml
├── README.md
├── logs/                         # structured JSON logs, gitignored
│   └── blog_engine.jsonl
├── docs/
│   ├── adr/
│   │   ├── ADR-001.md
│   │   ├── ADR-002.md
│   │   ├── ADR-003.md
│   │   ├── ADR-004.md
│   │   ├── ADR-005.md
│   │   ├── ADR-006.md
│   │   ├── ADR-007.md
│   │   ├── ADR-008.md
│   │   └── ADR-009.md
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
│   │   ├── model_router.py       # Borrowed from PrivyBot
│   │   └── logger.py             # structlog setup, JSON output
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
│       ├── draft_tools.py        # MCP tools: list, get, update, approve, delete, revert
│       └── publish_tools.py      # MCP tools: publish_wp, publish_devto, get_status
└── tests/
    ├── conftest.py               # fixtures, mock factories
    ├── test_inventory.py
    ├── test_draft_manager.py
    ├── test_generator.py
    ├── test_wordpress.py
    ├── test_devto.py
    ├── test_publisher.py
    └── test_idempotency.py       # duplicate publish prevention
```

---

### Data Flow

**Internal generation path:**
```
list_inventory(status="pending") → pick post_id
→ get_post_context(post_id) → loads inventory notes + frame template
→ generate_post(post_id) → model_router → draft JSON saved
→ get_draft(post_id) → review in Claude
→ approve_draft(post_id) → status: approved
→ publish_to_wordpress(post_id) → idempotency check → WP draft created → URL returned
→ update_inventory_status(post_id, "published") → inventory YAML updated
→ publish_to_devto(post_id) → canonical = WP URL → Dev.to draft
```

**External generation path (Claude browser session):**
```
Claude drafts post content in conversation
→ create_draft(post_id, title, content) → draft JSON saved
→ approve_draft(post_id)
→ publish_to_wordpress(post_id)
→ update_inventory_status(post_id, "published")
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

**Status lifecycle:** `draft` → `approved` → `published`

**Tags/categories source enum:**
- `"auto"` — generated by model during post generation
- `"manual"` — hand-entered by Robert
- `"per_post"` — sourced from inventory.yaml notes

**Draft status vs. inventory status:**
- Draft JSON `status` tracks **approval state**: `draft | approved | published`
- Inventory YAML `status` tracks **publishing lifecycle**: `pending | drafted | approved | published`
- Inventory is the system of record for pipeline state. Draft JSON is the system of record for content and approval.
- `update_inventory_status` tool writes to inventory. Draft manager writes to draft JSON. Neither writes to the other's domain.

---

### SQLite Context Schema

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- Post thread relationships
CREATE TABLE IF NOT EXISTS post_threads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS post_thread_members (
    post_id TEXT NOT NULL,
    thread_id INTEGER NOT NULL,
    sequence INTEGER,
    PRIMARY KEY (post_id, thread_id),
    FOREIGN KEY (thread_id) REFERENCES post_threads(id)
);

-- Post context memory (RFD Content Frame slots)
CREATE TABLE IF NOT EXISTS post_context (
    post_id TEXT PRIMARY KEY,
    raw_extraction TEXT,
    frame_moment TEXT,
    frame_surprise TEXT,
    frame_struggle TEXT,
    frame_lesson TEXT,
    frame_next TEXT,
    related_posts TEXT,           -- JSON array of post_ids
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Draft revision history
CREATE TABLE IF NOT EXISTS draft_revisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id TEXT NOT NULL,
    revision_number INTEGER NOT NULL,
    content TEXT NOT NULL,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    saved_by TEXT,                -- 'human' | 'claude' | 'internal'
    UNIQUE (post_id, revision_number)
);

-- Publish log (idempotency source of truth)
CREATE TABLE IF NOT EXISTS publish_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id TEXT NOT NULL,
    platform TEXT NOT NULL,       -- 'wordpress' | 'devto'
    status TEXT NOT NULL,         -- 'success' | 'failed'
    platform_id TEXT,             -- WP post ID or Dev.to article ID
    platform_url TEXT,
    error_message TEXT,
    published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (post_id, platform, status)
        ON CONFLICT IGNORE        -- idempotency: duplicate success = no-op
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_draft_revisions_post
    ON draft_revisions(post_id, revision_number);

CREATE INDEX IF NOT EXISTS idx_publish_log_post
    ON publish_log(post_id, platform);

CREATE INDEX IF NOT EXISTS idx_thread_members_thread
    ON post_thread_members(thread_id);
```

---

### MCP Tool Surface (exposed to Claude)

| Tool | Parameters | Description |
|---|---|---|
| `list_inventory` | `status: str = "pending"`, `thread: str = None` | Returns posts filtered by status and optionally by thread |
| `get_post_context` | `post_id: str` | Returns inventory notes + frame slots |
| `generate_post` | `post_id: str`, `model: str = None`, `override_frame: bool = False` | Internal generation via model router |
| `create_draft` | `post_id: str`, `title: str`, `content: str`, `tags: list = []`, `categories: list = []`, `tags_source: str = "manual"` | External: saves Claude-authored content as draft |
| `get_draft` | `post_id: str` | Returns current draft content for review |
| `update_draft` | `post_id: str`, `content: str`, `saved_by: str = "human"` | Updates draft, saves revision, increments count |
| `approve_draft` | `post_id: str`, `approved_by: str = "human"` | Sets approved status |
| `delete_draft` | `post_id: str` | Removes draft JSON, resets inventory to pending |
| `revert_revision` | `post_id: str`, `revision_number: int` | Restores a previous revision as current draft |
| `get_revision_history` | `post_id: str` | Returns all revisions with timestamps |
| `publish_to_wordpress` | `post_id: str`, `publish: bool = False` | Idempotency check → push to WP. `publish=False` creates WP draft. |
| `publish_to_devto` | `post_id: str`, `published: bool = False` | Requires WP URL. Sets canonical. |
| `get_publish_status` | `post_id: str` | Returns full status including publish log |
| `update_inventory_status` | `post_id: str`, `status: str` | Writes status to inventory.yaml |
| `list_threads` | — | Returns all thread groups with member counts |
| `add_to_thread` | `post_id: str`, `thread_name: str`, `sequence: int = None` | Adds post to named thread, creates thread if new |

---

## §3 — Error Handling Strategy

### Retry Policy (ADR-006)

All external API calls (WordPress, Dev.to) use exponential backoff inherited from BaseAPIHandler:

```
Attempt 1: immediate
Attempt 2: 2s delay
Attempt 3: 4s delay
Attempt 4: 8s delay (max attempts for transient errors)
Give up: log as failed, raise BlogEngineError
```

**Error classification:**

| Error type | Retry? | Action |
|---|---|---|
| HTTP 429 (rate limit) | Yes, with Retry-After header | Wait then retry |
| HTTP 500-503 (server error) | Yes, up to 4 attempts | Exponential backoff |
| HTTP 401 (auth failure) | No | Fail immediately, log credential error |
| HTTP 404 (not found) | No | Fail immediately |
| Network timeout | Yes, up to 4 attempts | Exponential backoff |
| SQLite WAL lock | Yes, up to 10 attempts | 100ms backoff (inherited from DBManager) |
| Model router all models failed | No | Fail generation, draft not saved |

**Dead letter:** Failed publishes are written to `publish_log` with `status='failed'` and `error_message`. The `get_publish_status` tool surfaces these. No automatic retry of failed publishes — manual re-trigger via `publish_to_wordpress` or `publish_to_devto`.

---

## §4 — Logging Strategy

**Library:** structlog with JSON output.

**Output:** `logs/blog_engine.jsonl` — one JSON object per line, append-only, gitignored.

**Log levels:**

| Level | When |
|---|---|
| DEBUG | API request/response bodies (dev only, controlled by LOG_LEVEL env var) |
| INFO | Tool calls, generation start/complete, publish start/complete |
| WARNING | Retry attempt, stale cache used, model fallback triggered |
| ERROR | API failure after all retries, SQLite error, generation failure |
| CRITICAL | Credential missing at startup, DB schema migration failure |

**Standard log fields:**
```json
{
  "timestamp": "2026-06-07T11:00:00Z",
  "level": "info",
  "event": "publish_to_wordpress.success",
  "post_id": "dev-001",
  "wp_post_id": 42,
  "wp_url": "https://blog.rfditservices.com/...",
  "duration_ms": 312
}
```

**Publishable vs. retryable distinction:**
- Retryable: network errors, rate limits, server errors (5xx)
- Publishable (permanent failure): auth errors (401), bad request (400), model router exhausted
- Publishable errors log at ERROR level and surface in `get_publish_status`

---

## §5 — Testing Strategy

**Test count is the floor metric.** "Target floor: X → Y" means Y passing tests, 0 failing, 0 skipped. Same convention as PrivyBot and OpenAgent.

**Test categories:**

| Category | What it covers | Mock strategy |
|---|---|---|
| Unit | Individual functions, pure logic | No mocks needed |
| Integration | Module interactions, SQLite operations | Mock external APIs only |
| Contract | API handler request/response shape | httpx mock transport |
| Idempotency | Duplicate publish prevention | Mock API + real SQLite |

**No end-to-end tests with live credentials in the test suite.** Phase 7 integration verification uses a manual checklist against staging, not pytest. Manual checklist is documented in §8.

**Fixture conventions (conftest.py):**
```python
@pytest.fixture
def db():          # in-memory SQLite, schema applied
@pytest.fixture
def inventory():   # minimal inventory.yaml with 3 test posts
@pytest.fixture
def draft():       # pre-built draft JSON for post dev-001
@pytest.fixture
def wp_mock():     # httpx mock returning WP success response
@pytest.fixture
def devto_mock():  # httpx mock returning Dev.to success response
```

All external API calls mocked. No network in test suite. No real WordPress. No real Dev.to.

---

## §6 — Deployment on Nitro

**MCP server entry point:**
```bash
uv run python -m blog_engine.server
```

**Claude Desktop MCP config** (`claude_desktop_config.json`):
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

**Startup verification:**
Claude Desktop restart → type `list_inventory` → should return pending posts from inventory.yaml. If tool not found, check cwd path. If returns empty, check inventory.yaml exists in data/.

---

## §7 — Architecture Decision Records

### ADR-001: JSON for drafts, SQLite for context

**Status:** Accepted

**Context:** Need persistent storage for draft state and post relationships. Two different access patterns — drafts are read/written as whole documents, context is queried relationally.

**Decision:** JSON files for draft state (one file per post, named by post_id). SQLite WAL for context memory, revision history, thread relationships, and publish log.

**Consequences:** Drafts are human-readable and portable. Context is queryable. Draft files can be committed to git as a snapshot. SQLite never committed.

---

### ADR-002: Always draft first, approval required before publish

**Status:** Accepted

**Context:** Publishing errors are hard to reverse. WordPress posts can be deleted but Dev.to syndication with canonical URL affects SEO immediately.

**Decision:** All generation produces a draft JSON with `status: draft`. Publish tools check for `status: approved` before executing. No publish path bypasses the approval gate. Approver field records who approved.

**Consequences:** Nothing publishes without explicit approval. Future review agent sets approver field automatically. Human approval is default for MVP.

---

### ADR-003: stdio transport now, SSE deferred

**Status:** Accepted

**Context:** Claude Desktop uses stdio MCP transport. Tower uses SSE via mcp-proxy. Building for both simultaneously adds complexity with no immediate benefit.

**Decision:** FastMCP stdio only for MVP. When absorbed into PrivyBot Phase 31, transport switches to SSE. The tool layer is transport-agnostic — only `server.py` changes.

**Consequences:** Claude Desktop can use it immediately on Nitro. Tower deployment requires one server.py rewrite, no tool changes.

---

### ADR-004: Model routing hierarchy

**Status:** Accepted

**Context:** Internal generation needs a model. External API costs money. Need fallback chain.

**Decision:** Groq (free, fast) → Gemini Direct → OpenRouter → Ollama (local, last resort). Same hierarchy as PrivyBot. Model router borrowed directly from PrivyBot infra/. Environment variable names are identical — no renaming.

**Consequences:** Generation is free-tier first. Cost only incurred if Groq is unavailable. Ollama on Nitro handles offline sessions.

---

### ADR-005: Inventory schema ownership

**Status:** Accepted

**Context:** 70-post inventory exists in this session as context. PrivyBot and ContentPipeline may eventually share it.

**Decision:** `data/inventory.yaml` is owned by rfd-blog-engine for MVP. Schema is designed to be readable by other tools without modification. `status` is the only field this tool writes via `update_inventory_status`. All other inventory fields are read-only from this tool's perspective.

**Consequences:** Inventory can be symlinked or copied to other repos later. No circular dependency on PrivyBot.

---

### ADR-006: Error handling and retry policy

**Status:** Accepted

**Context:** External APIs fail. Network transient errors, rate limits, service outages all occur in production.

**Decision:** Exponential backoff (2s, 4s, 8s) for transient errors (5xx, timeout, 429). Immediate failure for auth errors (401) and bad requests (400). Max 4 attempts for external APIs, 10 for SQLite WAL locks (inherited from DBManager). Failed publishes written to publish_log with error_message. No automatic retry of failed publishes — manual re-trigger only.

**Consequences:** Transient failures recover automatically. Permanent failures surface clearly in get_publish_status. Dead letter is the publish_log table.

---

### ADR-007: Idempotency of publish operations

**Status:** Accepted

**Context:** MCP tools may be called multiple times for the same post. Duplicate publishes create duplicate WordPress posts and break Dev.to canonical URLs.

**Decision:** Before any publish, query `publish_log` for `(post_id, platform, status='success')`. If found, return existing URL immediately — do not call external API. The `UNIQUE (post_id, platform, status) ON CONFLICT IGNORE` constraint enforces this at the database level as a second line of defense.

**Consequences:** Publish operations are safe to retry. Duplicate calls return the same URL. No duplicate WordPress posts. No broken canonicals.

---

### ADR-008: Single-writer model for JSON drafts

**Status:** Accepted

**Context:** JSON files have no atomic write locking. Concurrent edits from two Claude Desktop sessions would corrupt draft files. File locking (fcntl/Windows equivalent) adds complexity.

**Decision:** rfd-blog-engine is a single-writer tool. Only one Claude Desktop session should interact with drafts at a time. This is the expected usage pattern — Robert works in one session. Document the constraint explicitly. Do not implement file locking for MVP. If concurrent access becomes a real problem, migrate draft state to SQLite.

**Consequences:** Concurrent session corruption is possible but unlikely given usage pattern. SQLite migration path exists if needed. MVP stays simple.

---

### ADR-009: Migration path to PrivyBot Phase 31

**Status:** Accepted

**Context:** This tool is designed to fold into PrivyBot Phase 31. The migration needs to be defined before it's needed.

**Decision:** Migration checklist when Phase 31 is ready:
1. Transport: `server.py` rewritten for SSE. Tool files unchanged.
2. DB: `blog_engine.db` contents migrated into PrivyBot's SQLite. Schema is compatible (WAL, same patterns).
3. Inventory: `data/inventory.yaml` symlinked or copied to PrivyBot data directory.
4. Credentials: WP and Dev.to keys added to PrivyBot `.env`. Existing model router keys already present.
5. Borrowed infra files: Discard — PrivyBot's originals used instead.
6. API handlers: `wordpress.py` and `devto.py` moved to PrivyBot `api/` directory unchanged.

**Consequences:** Migration is a half-day of work, not a rewrite. Tool layer survives intact.

---

## §8 — Phase Roadmap

Floor metric: **test count**. "X → Y" means Y passing tests, 0 failing, 0 skipped.

### Phase 1 — Foundation
New repo, directory structure, borrowed infra files, pyproject.toml, .env.example, inventory.yaml seeded with 70 posts, SQLite schema initialized, logger.py setup, structlog installed.

**Target floor: 0 → 15**
Tests: schema creation, inventory load, logger output format, .env validation.

### Phase 2 — Draft Manager
JSON draft CRUD, SQLite context tables with indexes, revision history, `delete_draft`, `revert_revision`, `get_revision_history`. Status field ownership enforced.

**Target floor: 15 → 35**
Tests: create/read/update/delete draft, revision save, revert, idempotency constraint on revisions.

### Phase 3 — API Handlers
`wordpress.py` and `devto.py` with full retry logic, idempotency check via publish_log, canonical URL enforcement on Dev.to. All calls mocked in tests.

**Target floor: 35 → 55**
Tests: WP create/update, Dev.to create, retry behavior (mock 500 → success), idempotency (duplicate publish returns existing URL), canonical URL required.

### Phase 4 — Generator
Internal generation via model_router, RFD Content Frame prompt baked in, frame slot extraction from inventory context, `generate_post` and `get_post_context` tools.

**Target floor: 55 → 70**
Tests: frame prompt construction, model router fallback, draft saved after generation, generation failure does not save draft.

### Phase 5 — MCP Server + Tools
FastMCP server, all 16 tools registered and callable, stdio transport, `update_inventory_status` wired to inventory.yaml.

**Target floor: 70 → 90**
Tests: tool registration, tool parameter validation, inventory status update, list_inventory filter by status and thread.

### Phase 6 — Publisher + Approval Gate
Full publish flow: approve check → idempotency check → WordPress → inventory update → Dev.to. Publish log written. Error handling: WP fail aborts, Dev.to fail logs but does not roll back WP.

**Target floor: 90 → 110**
Tests: publish blocked without approval, WP fail aborts Dev.to, Dev.to fail logged only, publish_log written on success, get_publish_status reflects all states.

### Phase 7 — Integration Verification (Manual Checklist)

No new tests. Manual verification with real credentials against staging.

**Checklist:**
- [ ] Claude Desktop MCP config updated with correct cwd path
- [ ] Claude Desktop restarted, `list_inventory` returns posts
- [ ] `generate_post("dev-001")` produces draft, draft JSON saved to data/drafts/
- [ ] `get_draft("dev-001")` returns readable content in Claude
- [ ] `approve_draft("dev-001")` sets approved status
- [ ] `publish_to_wordpress("dev-001")` creates WP draft, returns URL
- [ ] WP draft visible in WordPress admin
- [ ] `publish_to_devto("dev-001")` creates Dev.to draft, canonical points to WP URL
- [ ] `get_publish_status("dev-001")` shows both platform IDs and URLs
- [ ] `publish_to_wordpress("dev-001")` called again — returns existing URL, no duplicate post
- [ ] logs/blog_engine.jsonl contains structured log entries for all operations
- [ ] `docs/state/current.md` updated to Phase 7 complete

---

## §9 — Credentials Required

| Credential | How to get | .env key |
|---|---|---|
| WordPress Application Password | WP Admin → Users → Profile → Application Passwords | `WP_URL`, `WP_USER`, `WP_APP_PASSWORD` |
| Dev.to API Key | dev.to/settings/extensions | `DEVTO_API_KEY` |
| Groq API Key | console.groq.com | `GROQ_API_KEY` |
| Gemini API Key | aistudio.google.com | `GEMINI_API_KEY` |
| OpenRouter API Key | openrouter.ai | `OPENROUTER_API_KEY` |
| Log level | — | `LOG_LEVEL=INFO` |

Groq, Gemini, OpenRouter keys already in Nitro PrivyBot `.env`. Copy them directly — same variable names.

---

## §10 — State File

Initialize at project creation:

```markdown
phase: 'Phase 1 — Foundation'
certified_floor: 0/0/0
what_is_next: 'Phase 2 — Draft Manager'
```

---

*rfd-blog-engine SDD v0.2 | June 2026 | RFD IT Services Ltd.*
*Supersedes v0.1. All accepted critique gaps addressed.*
*Director → Pipeline → Agent. Spec first. Test floor always real.*

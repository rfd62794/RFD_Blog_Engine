# rfd-blog-engine — Phase 5 Directive: MCP Server + Tools

*June 2026 | Read fully before executing anything.*

---

> ⛔ **STOP:** Run pytest before touching any file.
> Must report **81 passing, 0 failing, 0 skipped**.
> If count differs, stop and report — do not proceed.

---

## §0 Context

**What exists:**
Phase 4 complete. 81/0/0 certified floor. InventoryManager, DraftManager, PostGenerator, WordPressHandler, DevToHandler all built and tested. All async tests use `asyncio.run()` pattern (ADR-010).

**What this phase delivers:**
`server.py` — FastMCP server with stdio transport. Three tool modules — `generate_tools.py`, `draft_tools.py`, `publish_tools.py` — exposing all 16 MCP tools to Claude Desktop. `cli.py` — Click entry point. Claude Desktop config documented. All tools callable from Claude Desktop after restart.

**Why it matters:**
This is the integration layer. Everything built in Phases 1-4 becomes accessible to Claude via MCP after this phase. The external generation path (Claude authors content in browser, saves via MCP tool) becomes live. Internal generation path (Claude triggers `generate_post` via MCP) becomes live.

**What is NOT in scope:**
- Publisher orchestration (Phase 6) — `publish_to_wordpress` and `publish_to_devto` tools are registered but call stubs only in this phase
- Any real API calls during tests
- pytest-asyncio (ADR-010 — not used in this project)

---

## §1 Scope Statement

| File | Status | Action |
|---|---|---|
| `blog_engine/server.py` | New | FastMCP server, tool registration, stdio transport |
| `blog_engine/cli.py` | New | Click entry point |
| `blog_engine/tools/generate_tools.py` | New | generate_post, get_post_context tools |
| `blog_engine/tools/draft_tools.py` | New | list_inventory, get_draft, create_draft, update_draft, approve_draft, delete_draft, revert_revision, get_revision_history tools |
| `blog_engine/tools/publish_tools.py` | New | publish_to_wordpress, publish_to_devto, get_publish_status, update_inventory_status, list_threads, add_to_thread tools (stubs for publish tools) |
| `tests/test_tools.py` | New | 15 new tests |
| `docs/state/current.md` | Modify | Update to Phase 5 complete on finish |
| `blog_engine/core/inventory.py` | Read-only | Do not touch. |
| `blog_engine/core/generator.py` | Read-only | Do not touch. |
| `blog_engine/core/draft_manager.py` | Read-only | Do not touch. |
| `blog_engine/api/wordpress.py` | Read-only | Do not touch. |
| `blog_engine/api/devto.py` | Read-only | Do not touch. |
| All existing test files | Read-only | Do not touch existing tests. |

**Read-only — do not touch:**
All existing source files. All existing test files. Report before touching anything not listed as New or Modify above.

---

## §2 Implementation

### `blog_engine/server.py`

```python
from fastmcp import FastMCP
from blog_engine.tools.generate_tools import register_generate_tools
from blog_engine.tools.draft_tools import register_draft_tools
from blog_engine.tools.publish_tools import register_publish_tools

mcp = FastMCP("rfd-blog-engine")

register_generate_tools(mcp)
register_draft_tools(mcp)
register_publish_tools(mcp)

if __name__ == "__main__":
    mcp.run()
```

> ⚠️ RULE: Server is stdio transport only. Do not add SSE, HTTP, or any other transport. That is Phase 31 (PrivyBot absorption) scope.

> ⚠️ RULE: All dependency instantiation (DBManager, InventoryManager, DraftManager, etc.) happens inside tool registration functions, not at module level. Module-level instantiation breaks tests.

---

### `blog_engine/cli.py`

```python
import click
import subprocess
import sys

@click.group()
def cli():
    """rfd-blog-engine — Blog post generation and publishing MCP server."""
    pass

@cli.command()
def serve():
    """Start the MCP server (stdio transport)."""
    from blog_engine.server import mcp
    mcp.run()

@cli.command()
def version():
    """Print version."""
    from blog_engine import __version__
    click.echo(f"rfd-blog-engine {__version__}")

if __name__ == "__main__":
    cli()
```

---

### `blog_engine/tools/generate_tools.py`

Two tools registered:

**`generate_post`**
```python
async def generate_post(post_id: str, model: str = None, override_frame: bool = False) -> dict:
    """
    Generate a blog post draft using the internal model router.
    Uses RFD Content Frame prompt. Saves draft to data/drafts/{post_id}.json.
    Returns: {post_id, title, status, generation_source, revision_count}
    Raises if post not in inventory, draft exists without override, or all models fail.
    """
```

**`get_post_context`**
```python
async def get_post_context(post_id: str) -> dict:
    """
    Returns full context for a post: inventory fields + SQLite frame slots.
    Use before generate_post to understand what context exists.
    Returns: {post_id, title, category, notes, tags, frame_slots: {moment, surprise, struggle, lesson, next}}
    """
```

> ⚠️ RULE: Tool functions are `async def`. They are called by FastMCP which handles the event loop. Do not wrap in `asyncio.run()` inside tool functions — that is for tests only (ADR-010).

---

### `blog_engine/tools/draft_tools.py`

Eight tools registered:

| Tool function | Parameters | Returns |
|---|---|---|
| `list_inventory` | `status: str = "pending"`, `thread: str = None` | `list[dict]` of posts |
| `get_draft` | `post_id: str` | draft dict or `{"error": "not found"}` |
| `create_draft` | `post_id: str`, `title: str`, `content: str`, `tags: list = []`, `categories: list = []`, `tags_source: str = "manual"` | draft dict |
| `update_draft` | `post_id: str`, `content: str`, `saved_by: str = "human"` | updated draft dict |
| `approve_draft` | `post_id: str`, `approved_by: str = "human"` | updated draft dict |
| `delete_draft` | `post_id: str` | `{"deleted": True, "post_id": post_id}` |
| `revert_revision` | `post_id: str`, `revision_number: int` | updated draft dict |
| `get_revision_history` | `post_id: str` | `list[dict]` of revisions |

> ⚠️ RULE: Tools never raise exceptions to Claude. Catch all exceptions, return `{"error": str(e), "post_id": post_id}`. Claude reads error messages — stack traces are not useful to it.

> ⚠️ RULE: `list_inventory` with `thread` parameter queries `post_thread_members` in SQLite. If thread not found, return empty list with `{"warning": "thread not found"}` included.

---

### `blog_engine/tools/publish_tools.py`

Six tools registered. **`publish_to_wordpress` and `publish_to_devto` are stubs in this phase** — they return `{"status": "not_implemented", "message": "Publishing tools implemented in Phase 6"}`. All other four tools are fully implemented.

| Tool function | Phase 5 status | Parameters | Returns |
|---|---|---|---|
| `publish_to_wordpress` | **Stub** | `post_id: str`, `publish: bool = False` | stub response |
| `publish_to_devto` | **Stub** | `post_id: str`, `published: bool = False` | stub response |
| `get_publish_status` | Implemented | `post_id: str` | publish_log rows for post |
| `update_inventory_status` | Implemented | `post_id: str`, `status: str` | `{"updated": True, "post_id": post_id, "status": status}` |
| `list_threads` | Implemented | — | `list[dict]` of threads with member counts |
| `add_to_thread` | Implemented | `post_id: str`, `thread_name: str`, `sequence: int = None` | `{"added": True, "post_id": post_id, "thread": thread_name}` |

> ⚠️ RULE: Stub tools must clearly communicate they are stubs. Return `{"status": "not_implemented", "message": "..."}` — do not raise, do not return empty dict, do not silently succeed.

> ⚠️ RULE: `get_publish_status` returns all publish_log rows for the post_id across both platforms. If no rows exist, return `{"post_id": post_id, "platforms": {}}`.

---

### Claude Desktop Configuration

After Phase 5 complete, add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "rfd-blog-engine": {
      "command": "C:\\Github\\RFD_Blog_Engine\\.venv\\Scripts\\python.exe",
      "args": ["-m", "blog_engine.server"],
      "cwd": "C:\\Github\\RFD_Blog_Engine"
    }
  }
}
```

> ⚠️ RULE: Use `.venv\Scripts\python.exe` explicitly — not `uv run`, not system python. Learned from Phase 3 environment debugging.

---

## §3 Test Anchors

### `tests/test_tools.py` — 15 new tests

All tests are synchronous. Async tool functions tested via `asyncio.run()` (ADR-010).

| Test | Behaviour |
|---|---|
| `test_server_creates_mcp_instance` | `mcp` object exists and is FastMCP instance |
| `test_generate_post_tool_registered` | `generate_post` tool accessible on mcp |
| `test_get_post_context_tool_registered` | `get_post_context` tool accessible on mcp |
| `test_list_inventory_returns_list` | Returns list, mocked inventory |
| `test_get_draft_returns_dict` | Returns draft dict for known post |
| `test_get_draft_not_found_returns_error` | Returns `{"error": ...}` not exception |
| `test_create_draft_tool` | Draft created, dict returned |
| `test_approve_draft_tool` | Status changes to approved |
| `test_delete_draft_tool` | Returns `{"deleted": True}` |
| `test_update_inventory_status_tool` | Inventory status updated |
| `test_get_publish_status_empty` | Returns `{"platforms": {}}` for unpublished post |
| `test_list_threads_empty` | Returns empty list when no threads exist |
| `test_add_to_thread_creates_thread` | Thread created and post added |
| `test_publish_to_wordpress_stub` | Returns `{"status": "not_implemented"}` |
| `test_publish_to_devto_stub` | Returns `{"status": "not_implemented"}` |

**Target floor: 96 passing, 0 failing, 0 skipped**
(81 existing + 15 new)

> ⚠️ RULE: All external dependencies mocked. No real file system writes in tool tests — use temp_dir fixture. No real SQLite — use db fixture. No real inventory — use inventory fixture.

> ⚠️ RULE: No pytest-asyncio. No `@pytest.mark.asyncio`. `asyncio.run()` only. ADR-010.

---

## §4 Completion Criteria

- [ ] pytest reports **96 passing, 0 failing, 0 skipped** (report real number if differs)
- [ ] `server.py` creates FastMCP instance and registers all 16 tools
- [ ] All 16 tools callable from server (verified via test_tools.py)
- [ ] Publish tools return stub response clearly marked `not_implemented`
- [ ] Tool errors return `{"error": str(e)}` — no unhandled exceptions reach Claude
- [ ] `cli.py` has `serve` and `version` commands
- [ ] Claude Desktop config documented in `docs/claude_desktop_config.json`
- [ ] `.venv\Scripts\python.exe` used explicitly in Claude Desktop config
- [ ] `docs/state/current.md` updated to Phase 5 complete

---

## §5 Quick Reference

| Key | Value |
|---|---|
| Certified floor entering | 81/0/0 |
| Target floor exiting | 96/0/0 (report real number) |
| New tests | 15 |
| New files | 5 (`server.py`, `cli.py`, 3 tool modules) + 1 test file |
| MCP transport | stdio only — no SSE, no HTTP |
| Dependency instantiation | Inside tool registration functions — never module level |
| Tool error handling | Return `{"error": str(e)}` — never raise to Claude |
| Stub tools | `publish_to_wordpress`, `publish_to_devto` — Phase 6 |
| Claude Desktop python | `.venv\Scripts\python.exe` explicitly |
| Async in tools | `async def` — FastMCP handles event loop |
| Async in tests | `asyncio.run()` — ADR-010, no exceptions |
| pytest-asyncio | Not used — ADR-010 locked |

---

*rfd-blog-engine Phase 5 Directive | June 2026 | RFD IT Services Ltd.*
*Director → Pipeline → Agent. Spec first. Test floor always real.*

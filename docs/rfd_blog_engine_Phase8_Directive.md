# rfd-blog-engine — Phase 8 Directive: WordPress Management Tools

*June 2026 | Read fully before executing anything.*

---

> ⛔ **STOP:** Run pytest before touching any file.
> Must report **111 passing, 0 failing, 0 skipped**.
> If count differs, stop and report — do not proceed.

---

## §0 Context

**What exists:**
Phase 7 complete. 111/0/0 certified floor. Full publish pipeline live — generate, draft, approve, publish to WordPress and Dev.to. Banner noise fixed. All 16 tools callable from Claude Desktop.

**What this phase delivers:**
Four new WordPress management tools giving Claude read and update access to existing WordPress content. Without these, Claude publishes blind — cannot see what's already live, cannot fix published posts, cannot assign real categories.

**Why it matters:**
The blog has 13+ existing published posts. Before publishing new content, Claude needs to read what's there to avoid duplicates, assign correct categories, and verify publishes succeeded. `update_wordpress_post` closes the loop — if a published post needs a fix, Claude can apply it without manual WP admin access.

**What is NOT in scope:**
- Media upload / featured image tools (needs multipart form upload, separate phase)
- WordPress user management
- Comment management
- Plugin or theme management
- Dev.to read tools (deferred)
- pytest-asyncio (ADR-010 — not used in this project)

---

## §1 Scope Statement

| File | Status | Action |
|---|---|---|
| `blog_engine/api/wordpress.py` | Modify | Add 3 new methods: `get_posts`, `get_post`, `get_categories` |
| `blog_engine/tools/publish_tools.py` | Modify | Add 4 new tools: `get_wordpress_posts`, `get_wordpress_post`, `update_wordpress_post`, `get_wordpress_categories` |
| `blog_engine/server.py` | Read-only | Do not touch — tools auto-register via publish_tools |
| `tests/test_wordpress.py` | Modify | Add 6 new tests for new handler methods |
| `tests/test_tools.py` | Modify | Add 4 new tests for new tools |
| `docs/state/current.md` | Modify | Update to Phase 8 complete on finish |
| All other files | Read-only | Do not touch. |

**Read-only — do not touch:**
`server.py`, `draft_manager.py`, `inventory.py`, `generator.py`, `publisher.py`, `devto.py`, all test files not listed above.

Report before touching anything not listed. Do not silently modify out-of-scope files.

---

## §2 Implementation

### `blog_engine/api/wordpress.py` — 3 new methods

Add to `WordPressHandler`:

```python
async def get_posts(
    self,
    status: str = "any",
    per_page: int = 20,
    page: int = 1,
    search: str = None
) -> list[dict]:
    """
    List WordPress posts.
    status: "publish" | "draft" | "any"
    Returns list of {id, title, status, link, date, modified, excerpt}
    """
    ...

async def get_post(self, wp_post_id: int) -> dict:
    """
    Fetch single WordPress post by ID.
    Returns {id, title, content, status, link, date, modified,
             categories, tags, excerpt}
    """
    ...

async def get_categories(self) -> list[dict]:
    """
    List all WordPress categories.
    Returns list of {id, name, slug, count}
    """
    ...
```

> ⚠️ RULE: `get_posts` uses WP REST API endpoint `GET {base_url}/wp-json/wp/v2/posts` with query params `status`, `per_page`, `page`, `search`. All requests use Basic auth same as existing methods.

> ⚠️ RULE: `get_post` uses `GET {base_url}/wp-json/wp/v2/posts/{wp_post_id}`. Returns raw WP response parsed to dict — do not filter fields, return everything.

> ⚠️ RULE: `get_categories` uses `GET {base_url}/wp-json/wp/v2/categories?per_page=100`. Returns all categories in one call — blog won't have more than 100.

> ⚠️ RULE: None of these three methods write to `publish_log`. They are read-only. No side effects.

> ⚠️ RULE: Retry policy inherited from BaseAPIHandler applies to all three. Same backoff as existing methods.

---

### `blog_engine/tools/publish_tools.py` — 4 new tools

Add to existing tool module. All use `_get_wp_handler()` factory — same pattern as `_get_publisher()` but returns `WordPressHandler` only, no Dev.to or DraftManager needed.

```python
def _get_wp_handler() -> WordPressHandler:
    """Factory for WordPress-only operations."""
    from blog_engine.api.wordpress import WordPressHandler
    from blog_engine.infra.db_manager import DBManager
    import os
    wp_url = os.getenv("WP_URL")
    wp_user = os.getenv("WP_USER")
    wp_password = os.getenv("WP_APP_PASSWORD")
    if not all([wp_url, wp_user, wp_password]):
        raise EnvironmentError("WP_URL, WP_USER, WP_APP_PASSWORD required")
    db = DBManager()
    return WordPressHandler(db=db, base_url=wp_url, user=wp_user, app_password=wp_password)
```

**`get_wordpress_posts`**
```python
async def get_wordpress_posts(
    status: str = "any",
    per_page: int = 20,
    search: str = None
) -> list[dict]:
    """
    List posts on WordPress blog.
    status: "publish" | "draft" | "any" (default: any)
    per_page: max results (default: 20)
    search: optional search term
    Returns list of {id, title, status, link, date}
    On error: [{"error": str(e)}]
    """
```

**`get_wordpress_post`**
```python
async def get_wordpress_post(wp_post_id: int) -> dict:
    """
    Fetch full content of a single WordPress post by ID.
    Returns full post dict including rendered content.
    On error: {"error": str(e)}
    """
```

**`update_wordpress_post`**
```python
async def update_wordpress_post(
    wp_post_id: int,
    title: str = None,
    content: str = None,
    status: str = None,
    tags: list = None,
    categories: list = None
) -> dict:
    """
    Update an existing WordPress post.
    Only fields provided are updated — all parameters optional.
    Returns {wp_post_id, wp_url, status}
    On error: {"error": str(e)}
    Requires explicit approval — do not call without Robert's confirmation.
    """
```

**`get_wordpress_categories`**
```python
async def get_wordpress_categories() -> list[dict]:
    """
    List all categories on the WordPress blog.
    Returns list of {id, name, slug, count}
    Use before publishing to assign correct category IDs.
    On error: [{"error": str(e)}]
    """
```

> ⚠️ RULE: `update_wordpress_post` tool description must include "Requires explicit approval — do not call without Robert's confirmation." This is an existing-content modification tool. Never call speculatively.

> ⚠️ RULE: All four tools follow existing error pattern — return `{"error": str(e)}` or `[{"error": str(e)}]` on failure. Never raise to Claude.

> ⚠️ RULE: All four tools are `async def`. Tests use `asyncio.run()` — ADR-010.

---

## §3 Test Anchors

### `tests/test_wordpress.py` — 6 new tests (append only)

| Test | Behaviour |
|---|---|
| `test_wp_get_posts_returns_list` | Mock GET → 200 list, returns parsed list |
| `test_wp_get_posts_with_status_filter` | status param passed as query param |
| `test_wp_get_posts_with_search` | search param passed as query param |
| `test_wp_get_post_returns_dict` | Mock GET single post → 200, returns dict |
| `test_wp_get_post_not_found` | Mock GET → 404, raises immediately (no retry) |
| `test_wp_get_categories_returns_list` | Mock GET → 200 list, returns parsed list |

### `tests/test_tools.py` — 4 new tests (append only)

| Test | Behaviour |
|---|---|
| `test_get_wordpress_posts_tool` | Returns list, mocked handler |
| `test_get_wordpress_post_tool` | Returns dict for valid ID |
| `test_update_wordpress_post_tool` | Mock update returns correct fields |
| `test_get_wordpress_categories_tool` | Returns list of category dicts |

**Target floor: 121 passing, 0 failing, 0 skipped**
(111 existing + 6 WP handler + 4 tool tests)

> ⚠️ RULE: All HTTP calls mocked. No real WordPress during tests.
> ⚠️ RULE: No pytest-asyncio. `asyncio.run()` only. ADR-010.
> ⚠️ RULE: Do not modify existing tests. Append only to both test files.

---

## §4 Completion Criteria

- [ ] pytest reports **121 passing, 0 failing, 0 skipped** (report real number if differs)
- [ ] `get_posts`, `get_post`, `get_categories` added to `WordPressHandler`
- [ ] All four new MCP tools registered and callable from Claude Desktop
- [ ] `get_wordpress_posts` returns real post list when called live
- [ ] `get_wordpress_categories` returns real category list when called live
- [ ] `update_wordpress_post` description contains approval warning
- [ ] `_get_wp_handler()` factory added, no duplicate credential code
- [ ] None of the new read methods write to `publish_log`
- [ ] `docs/state/current.md` updated to Phase 8 complete

---

## §5 Quick Reference

| Key | Value |
|---|---|
| Certified floor entering | 111/0/0 |
| Target floor exiting | 121/0/0 (report real number) |
| New tests | 10 (6 WP handler + 4 tools) |
| Modified files | `wordpress.py`, `publish_tools.py`, 2 test files |
| New files | None |
| WP posts endpoint | `GET {WP_URL}/wp-json/wp/v2/posts` |
| WP single post endpoint | `GET {WP_URL}/wp-json/wp/v2/posts/{id}` |
| WP categories endpoint | `GET {WP_URL}/wp-json/wp/v2/categories?per_page=100` |
| Auth | HTTP Basic — same as existing methods |
| publish_log writes | None — read tools have zero side effects |
| update_wordpress_post | Requires explicit human approval before calling |
| Network in tests | Zero — all mocked |
| pytest-asyncio | Not used — ADR-010 locked |
| Deferred | Media upload, featured images, Dev.to read tools |

---

*rfd-blog-engine Phase 8 Directive | June 2026 | RFD IT Services Ltd.*
*Director → Pipeline → Agent. Spec first. Test floor always real.*

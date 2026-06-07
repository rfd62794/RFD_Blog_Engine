# rfd-blog-engine — Phase 6 Directive: Publisher + Approval Gate

*June 2026 | Read fully before executing anything.*

---

> ⛔ **STOP:** Run pytest before touching any file.
> Must report **96 passing, 0 failing, 0 skipped**.
> If count differs, stop and report — do not proceed.

---

## §0 Context

**What exists:**
Phase 5 complete. 96/0/0 certified floor. All 16 MCP tools registered and callable from Claude Desktop. `publish_to_wordpress` and `publish_to_devto` are stubs returning `not_implemented`. MCP connection verified live — `list_inventory` returns real data.

**What this phase delivers:**
Full publish flow replacing the two stubs. `publish_to_wordpress` pushes approved draft to WordPress REST API and returns live URL. `publish_to_devto` pushes to Dev.to with canonical URL set to WordPress URL. Both update publish_log. Both update inventory status on success. Approval gate enforced — neither tool proceeds without `status: approved` on the draft.

**Why it matters:**
This is the final functional phase. After this, the full pipeline works: generate → draft → approve → publish WordPress → syndicate Dev.to. Phase 7 is manual verification only.

**What is NOT in scope:**
- Hashnode, LinkedIn, Reddit distribution (deferred per SDD)
- Scheduling system (deferred)
- Review agent / automated approval (deferred)
- pytest-asyncio (ADR-010 — not used in this project)
- Any changes to tools other than `publish_to_wordpress` and `publish_to_devto`

---

## §1 Scope Statement

| File | Status | Action |
|---|---|---|
| `blog_engine/tools/publish_tools.py` | Modify | Replace two stubs with real implementations |
| `blog_engine/core/publisher.py` | New | Orchestration logic: approve check → WP → inventory → Dev.to |
| `tests/test_publisher.py` | New | 15 new tests |
| `tests/test_tools.py` | Modify | Replace 2 stub tests with real publish tool tests |
| `docs/state/current.md` | Modify | Update to Phase 6 complete on finish |
| `blog_engine/api/wordpress.py` | Read-only | Do not touch. |
| `blog_engine/api/devto.py` | Read-only | Do not touch. |
| `blog_engine/core/draft_manager.py` | Read-only | Do not touch. |
| `blog_engine/core/inventory.py` | Read-only | Do not touch. |
| All other existing files | Read-only | Do not touch. |

**Read-only — do not touch:**
Everything except `publish_tools.py`, new `publisher.py`, new `test_publisher.py`, and `test_tools.py` (stub test replacements only).

Report before touching anything not listed above.

---

## §2 Implementation

### `blog_engine/core/publisher.py`

Single class `Publisher` orchestrating the full publish flow.

```python
from blog_engine.infra.db_manager import DBManager
from blog_engine.infra.logger import get_logger
from blog_engine.core.draft_manager import DraftManager
from blog_engine.core.inventory import InventoryManager
from blog_engine.api.wordpress import WordPressHandler
from blog_engine.api.devto import DevToHandler

class Publisher:
    def __init__(
        self,
        db: DBManager,
        draft_manager: DraftManager,
        inventory: InventoryManager,
        wp_handler: WordPressHandler,
        devto_handler: DevToHandler
    ):
        self.db = db
        self.drafts = draft_manager
        self.inventory = inventory
        self.wp = wp_handler
        self.devto = devto_handler
        self.logger = get_logger(__name__)

    async def publish_wordpress(
        self,
        post_id: str,
        publish: bool = False
    ) -> dict:
        """
        Full WordPress publish flow:
        1. Load draft — raise ValueError if not found
        2. Check approval — raise ValueError if status != "approved"
        3. Call WordPressHandler.create_post
        4. Update draft JSON with wp_post_id and wp_url
        5. Update inventory status to "published"
        6. Return {post_id, wp_post_id, wp_url, status}
        """
        ...

    async def publish_devto(
        self,
        post_id: str,
        published: bool = False
    ) -> dict:
        """
        Full Dev.to publish flow:
        1. Load draft — raise ValueError if not found
        2. Check approval — raise ValueError if status != "approved"
        3. Check wp_url exists on draft — raise ValueError if None
           (WordPress must be published first)
        4. Call DevToHandler.create_article with canonical_url=draft.wp_url
        5. Update draft JSON with devto_id and devto_url
        6. Return {post_id, devto_id, devto_url, canonical_url, status}
        """
        ...

    def _check_approved(self, draft: dict) -> None:
        """
        Raises ValueError if draft status is not "approved".
        Message: "Draft {post_id} must be approved before publishing. Current status: {status}"
        """
        ...

    def _update_draft_publish_fields(
        self,
        post_id: str,
        wp_post_id: int = None,
        wp_url: str = None,
        devto_id: int = None,
        devto_url: str = None
    ) -> None:
        """
        Updates draft JSON with publish result fields.
        Sets published_at timestamp if both wp_url and devto_url are now set.
        Uses atomic write pattern (inherited from DraftManager pattern).
        """
        ...
```

> ⚠️ RULE: `publish_devto` must check `draft.wp_url` before calling Dev.to. If `wp_url` is None, raise `ValueError("WordPress must be published before Dev.to. Call publish_to_wordpress first.")`. Enforce the ordering.

> ⚠️ RULE: `publish_wordpress` failure must NOT call `publish_devto`. These are independent tool calls — the orchestration order is enforced by the tool descriptions, not by a transaction. If WP fails, log it, raise, return error. Dev.to is never called.

> ⚠️ RULE: If Dev.to fails after WordPress succeeds, do NOT roll back WordPress. Log the Dev.to failure. Return error. WordPress URL is already live — rolling back creates more problems than it solves. This matches ADR-006.

> ⚠️ RULE: Both methods update inventory status to `"published"` on WordPress success only. Dev.to success does not change inventory status — WordPress publish is the canonical publish event.

> ⚠️ RULE: Log at INFO level: publish start, WordPress result (post_id, wp_url), Dev.to result (post_id, devto_url). Log at ERROR level: any failure after retries exhausted.

---

### `blog_engine/tools/publish_tools.py` — Replace stubs

Remove stub implementations of `publish_to_wordpress` and `publish_to_devto`. Replace with real implementations that instantiate `Publisher` and delegate.

```python
async def publish_to_wordpress(post_id: str, publish: bool = False) -> dict:
    """
    Publish approved draft to WordPress.
    Draft must have status: approved. Calls approval gate.
    publish=False creates WP draft. publish=True publishes immediately.
    Returns: {post_id, wp_post_id, wp_url, status}
    On error: {"error": str(e), "post_id": post_id}
    """
    try:
        publisher = _get_publisher()
        return await publisher.publish_wordpress(post_id, publish=publish)
    except Exception as e:
        return {"error": str(e), "post_id": post_id}

async def publish_to_devto(post_id: str, published: bool = False) -> dict:
    """
    Syndicate approved draft to Dev.to.
    WordPress must be published first (wp_url required on draft).
    canonical_url set automatically to wp_url.
    Returns: {post_id, devto_id, devto_url, canonical_url}
    On error: {"error": str(e), "post_id": post_id}
    """
    try:
        publisher = _get_publisher()
        return await publisher.publish_devto(post_id, published=published)
    except Exception as e:
        return {"error": str(e), "post_id": post_id}
```

`_get_publisher()` is a module-level factory function that instantiates all dependencies from environment variables. Same pattern as other tool modules.

> ⚠️ RULE: Tool functions still return `{"error": str(e)}` on failure — never raise to Claude. Matches existing tool error contract.

> ⚠️ RULE: `_get_publisher()` reads credentials from environment: `WP_URL`, `WP_USER`, `WP_APP_PASSWORD`, `DEVTO_API_KEY`. Raise `EnvironmentError` with clear message if any are missing.

---

## §3 Test Anchors

### `tests/test_publisher.py` — 15 new tests

All synchronous. Async methods via `asyncio.run()` (ADR-010). All external calls mocked.

| Test | Behaviour |
|---|---|
| `test_publish_wordpress_requires_approved` | Raises ValueError if draft status is "draft" |
| `test_publish_wordpress_requires_approved_not_published` | Raises ValueError if draft status is "published" |
| `test_publish_wordpress_calls_wp_handler` | WordPressHandler.create_post called with correct args |
| `test_publish_wordpress_updates_draft_wp_fields` | Draft JSON updated with wp_post_id and wp_url |
| `test_publish_wordpress_updates_inventory_status` | Inventory status set to "published" after WP success |
| `test_publish_wordpress_returns_correct_dict` | Returns {post_id, wp_post_id, wp_url, status} |
| `test_publish_wordpress_wp_failure_no_devto` | DevToHandler never called if WP fails |
| `test_publish_devto_requires_approved` | Raises ValueError if not approved |
| `test_publish_devto_requires_wp_url` | Raises ValueError if wp_url is None on draft |
| `test_publish_devto_sets_canonical` | DevToHandler called with canonical_url=draft.wp_url |
| `test_publish_devto_updates_draft_devto_fields` | Draft JSON updated with devto_id and devto_url |
| `test_publish_devto_no_rollback_on_failure` | WP URL preserved if Dev.to fails |
| `test_publish_devto_sets_published_at` | published_at set when both wp_url and devto_url present |
| `test_publish_wordpress_idempotency` | Second call returns existing URL (from publish_log) |
| `test_publish_devto_idempotency` | Second call returns existing URL (from publish_log) |

### `tests/test_tools.py` — Replace 2 stub tests

Remove `test_publish_to_wordpress_stub` and `test_publish_to_devto_stub`.
Add:

| Test | Behaviour |
|---|---|
| `test_publish_to_wordpress_unapproved_returns_error` | Returns `{"error": ...}` for unapproved draft |
| `test_publish_to_devto_no_wp_url_returns_error` | Returns `{"error": ...}` when wp_url missing |

Net test count: 96 - 2 removed + 15 new publisher + 2 new tool = **111 passing**

**Target floor: 111 passing, 0 failing, 0 skipped**

> ⚠️ RULE: No pytest-asyncio. No `@pytest.mark.asyncio`. `asyncio.run()` only. ADR-010.

> ⚠️ RULE: All external API calls mocked. No real WordPress. No real Dev.to. No network.

> ⚠️ RULE: Use in-memory SQLite `db` fixture. Use `temp_dir` for draft JSON files. No real file system side effects.

---

## §4 Completion Criteria

- [ ] pytest reports **111 passing, 0 failing, 0 skipped** (report real number if differs)
- [ ] `publish_to_wordpress` stub replaced with real implementation
- [ ] `publish_to_devto` stub replaced with real implementation
- [ ] Approval gate enforced — both tools check `status: approved` before proceeding
- [ ] `publish_devto` checks `wp_url` present before calling Dev.to
- [ ] Dev.to failure does not roll back WordPress URL
- [ ] WordPress success updates inventory status to "published"
- [ ] Both tools return `{"error": str(e)}` on failure — never raise to Claude
- [ ] `_get_publisher()` raises `EnvironmentError` if credentials missing
- [ ] `docs/state/current.md` updated to Phase 6 complete

---

## §5 Quick Reference

| Key | Value |
|---|---|
| Certified floor entering | 96/0/0 |
| Target floor exiting | 111/0/0 (report real number) |
| New tests | 17 (15 publisher + 2 tool replacements, -2 stubs) |
| New files | 1 (`publisher.py`) + 1 test file |
| Modified files | `publish_tools.py` (2 stubs → real), `test_tools.py` (2 replacements) |
| Approval gate | `status: approved` required before any publish call |
| WP → Dev.to ordering | `wp_url` must exist on draft before Dev.to call |
| Dev.to failure | Log only — do not roll back WordPress |
| Inventory update | WordPress success only — Dev.to does not change inventory |
| Credential source | Environment variables: WP_URL, WP_USER, WP_APP_PASSWORD, DEVTO_API_KEY |
| Network in tests | Zero — all mocked |
| pytest-asyncio | Not used — ADR-010 locked |

---

*rfd-blog-engine Phase 6 Directive | June 2026 | RFD IT Services Ltd.*
*Director → Pipeline → Agent. Spec first. Test floor always real.*

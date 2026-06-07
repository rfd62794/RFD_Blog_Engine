# rfd-blog-engine — Phase 3 Directive: API Handlers

*June 2026 | Read fully before executing anything.*

---

> ⛔ **STOP:** Run pytest before touching any file.
> Must report **37 passing, 0 failing, 0 skipped**.
> If count differs, stop and report — do not proceed.

---

## §0 Context

**What exists:**
Phase 2 complete. 37/0/0 certified floor. DraftManager with all 9 methods, atomic writes, revision history, context storage, enum validation.

**What this phase delivers:**
Two API handler modules — `wordpress.py` and `devto.py` — that handle all external publish operations. Full retry logic inherited from BaseAPIHandler. Idempotency check via publish_log before every publish. Canonical URL enforcement on Dev.to. All external calls mocked in tests.

**Why it matters:**
These are the only modules that touch external services. Every constraint in ADR-006 (retry policy) and ADR-007 (idempotency) lives here. If these are wrong, duplicate posts and broken canonicals follow. Get them right before wiring them to anything.

**What is NOT in scope:**
- MCP tool registration (Phase 5)
- Generator or model router calls (Phase 4)
- Publisher orchestration (Phase 6)
- Approval gate enforcement (Phase 6)
- Any call to DraftManager
- Any real network calls during tests

---

## §1 Scope Statement

| File | Status | Action |
|---|---|---|
| `blog_engine/api/wordpress.py` | New | WP REST API handler |
| `blog_engine/api/devto.py` | New | Dev.to REST API handler |
| `tests/test_wordpress.py` | New | 10 new tests |
| `tests/test_devto.py` | New | 10 new tests |
| `tests/test_idempotency.py` | New | 3 new tests |
| `docs/state/current.md` | Modify | Update to Phase 3 complete on finish |
| `blog_engine/infra/base_api_handler.py` | Read-only | Do not touch. |
| `blog_engine/infra/db_manager.py` | Read-only | Do not touch. |
| `blog_engine/infra/logger.py` | Read-only | Do not touch. |
| `blog_engine/core/draft_manager.py` | Read-only | Do not touch. |
| All existing test files | Read-only | Do not touch. |

**Read-only — do not touch:**
`base_api_handler.py`, `db_manager.py`, `logger.py`, `draft_manager.py`, all existing test files.

Report before fixing any bug found in read-only files. Do not silently modify out-of-scope files.

---

## §2 Implementation

### `blog_engine/api/wordpress.py`

```python
from blog_engine.infra.base_api_handler import BaseAPIHandler
from blog_engine.infra.db_manager import DBManager
from blog_engine.infra.logger import get_logger

class WordPressHandler(BaseAPIHandler):
    def __init__(self, db: DBManager, base_url: str, user: str, app_password: str):
        super().__init__()
        self.db = db
        self.base_url = base_url.rstrip("/")
        self.auth = (user, app_password)
        self.logger = get_logger(__name__)

    async def create_post(
        self,
        post_id: str,
        title: str,
        content: str,
        excerpt: str = "",
        tags: list[str] = [],
        categories: list[str] = [],
        status: str = "draft"
    ) -> dict:
        """
        Returns: {"wp_post_id": int, "wp_url": str, "status": str}
        Idempotency: checks publish_log first. If success record exists,
        returns existing URL without calling API.
        """
        ...

    async def update_post(
        self,
        post_id: str,
        wp_post_id: int,
        fields: dict
    ) -> dict:
        """
        Updates an existing WP post by wp_post_id.
        Returns: {"wp_post_id": int, "wp_url": str}
        """
        ...

    async def get_post(self, wp_post_id: int) -> dict:
        """
        Fetches a WP post by ID.
        Returns raw WP API response dict.
        """
        ...

    def _check_idempotency(self, post_id: str, platform: str) -> dict | None:
        """
        Queries publish_log for existing success record.
        Returns {"platform_id": str, "platform_url": str} if found, else None.
        """
        ...

    def _write_publish_log(
        self,
        post_id: str,
        platform: str,
        status: str,
        platform_id: str = None,
        platform_url: str = None,
        error_message: str = None
    ) -> None:
        """
        Writes result to publish_log table.
        ON CONFLICT IGNORE handles duplicate success entries at DB level.
        """
        ...
```

> ⚠️ RULE: `create_post` must call `_check_idempotency("wordpress")` before any HTTP call. If a success record exists, return existing URL immediately. Do not call the WP API.

> ⚠️ RULE: `status` parameter must be one of `{"draft", "publish"}`. Raise `ValueError` on invalid value. Default is `"draft"` — never publish unless explicitly passed `status="publish"`.

> ⚠️ RULE: Retry policy is inherited from BaseAPIHandler. Do not reimplement retry logic. Call `self._make_request()` or equivalent base method. Exponential backoff (2s, 4s, 8s), max 4 attempts for 5xx and timeout. Immediate failure for 401 and 400.

> ⚠️ RULE: On any failure after all retries, write to `publish_log` with `status="failed"` and `error_message`. Then raise `WordPressAPIError`.

> ⚠️ RULE: On success, write to `publish_log` with `status="success"`, `platform_id=str(wp_post_id)`, `platform_url=wp_url`. Then return result dict.

> ⚠️ RULE: WP REST API base endpoint: `{base_url}/wp-json/wp/v2/posts`. Auth via HTTP Basic with Application Password. Never hardcode credentials.

> ⚠️ RULE: `WordPressAPIError` must be defined in this file. Subclass of `Exception`. Carries `status_code` and `message`.

---

### `blog_engine/api/devto.py`

```python
from blog_engine.infra.base_api_handler import BaseAPIHandler
from blog_engine.infra.db_manager import DBManager
from blog_engine.infra.logger import get_logger

class DevToHandler(BaseAPIHandler):
    def __init__(self, db: DBManager, api_key: str):
        super().__init__()
        self.db = db
        self.api_key = api_key
        self.logger = get_logger(__name__)
        self.base_url = "https://dev.to/api"

    async def create_article(
        self,
        post_id: str,
        title: str,
        body_markdown: str,
        canonical_url: str,
        tags: list[str] = [],
        published: bool = False
    ) -> dict:
        """
        Returns: {"devto_id": int, "devto_url": str, "published": bool}
        Idempotency: checks publish_log first.
        canonical_url is required — raises ValueError if None or empty.
        """
        ...

    async def update_article(
        self,
        post_id: str,
        devto_id: int,
        fields: dict
    ) -> dict:
        """
        Updates an existing Dev.to article.
        Returns: {"devto_id": int, "devto_url": str}
        """
        ...

    def _check_idempotency(self, post_id: str, platform: str) -> dict | None:
        """Same pattern as WordPressHandler._check_idempotency."""
        ...

    def _write_publish_log(self, ...) -> None:
        """Same pattern as WordPressHandler._write_publish_log."""
        ...
```

> ⚠️ RULE: `create_article` must raise `ValueError` if `canonical_url` is `None` or empty string. This is non-negotiable — Dev.to without canonical breaks WordPress SEO.

> ⚠️ RULE: `create_article` must call `_check_idempotency("devto")` before any HTTP call. If success record exists, return existing devto_id and url immediately.

> ⚠️ RULE: Dev.to API auth is via header `api-key: {api_key}`. Never Basic auth. Never Bearer.

> ⚠️ RULE: Dev.to article endpoint: `POST https://dev.to/api/articles`. Body shape:
> ```json
> {
>   "article": {
>     "title": "...",
>     "body_markdown": "...",
>     "published": false,
>     "canonical_url": "https://blog.rfditservices.com/...",
>     "tags": ["tag1", "tag2"]
>   }
> }
> ```

> ⚠️ RULE: Tags list must be max 4 items for Dev.to API limit. If `tags` has more than 4 items, take the first 4 and log a warning. Do not raise — silently truncate and warn.

> ⚠️ RULE: On failure after all retries, write `publish_log` with `status="failed"`. Raise `DevToAPIError`.

> ⚠️ RULE: On success, write `publish_log` with `status="success"`. Return result dict.

> ⚠️ RULE: `DevToAPIError` defined in this file. Subclass `Exception`. Carries `status_code` and `message`.

---

### Shared pattern: `_check_idempotency`

Both handlers use identical logic. Do not deduplicate into a base class in this phase — keep it explicit in each handler. Deduplication is Phase 31 scope (PrivyBot absorption).

```python
def _check_idempotency(self, post_id: str, platform: str) -> dict | None:
    row = self.db.fetchone(
        "SELECT platform_id, platform_url FROM publish_log "
        "WHERE post_id = ? AND platform = ? AND status = 'success'",
        (post_id, platform)
    )
    if row:
        self.logger.info(
            "idempotency.hit",
            post_id=post_id,
            platform=platform,
            existing_url=row["platform_url"]
        )
        return {"platform_id": row["platform_id"], "platform_url": row["platform_url"]}
    return None
```

---

## §3 Test Anchors

### `tests/test_wordpress.py` — 10 tests

| Test | Behaviour |
|---|---|
| `test_wp_create_post_draft` | Mock POST → 201, returns wp_post_id and wp_url, status=draft |
| `test_wp_create_post_publish` | Mock POST with status=publish → returns published status |
| `test_wp_invalid_status_raises` | `status="live"` raises `ValueError` |
| `test_wp_write_publish_log_on_success` | publish_log row written with status=success after create |
| `test_wp_write_publish_log_on_failure` | publish_log row written with status=failed after 4xx |
| `test_wp_retry_on_500` | Mock 500 → 500 → 201, succeeds on third attempt |
| `test_wp_no_retry_on_401` | Mock 401, fails immediately, no retries |
| `test_wp_idempotency_returns_existing` | publish_log has success row → returns existing URL, no HTTP call |
| `test_wp_update_post` | Mock PATCH → 200, returns updated wp_url |
| `test_wp_get_post` | Mock GET → 200, returns raw response dict |

### `tests/test_devto.py` — 10 tests

| Test | Behaviour |
|---|---|
| `test_devto_create_article_draft` | Mock POST → 201, returns devto_id and devto_url |
| `test_devto_canonical_required` | `canonical_url=None` raises `ValueError` before HTTP call |
| `test_devto_canonical_empty_raises` | `canonical_url=""` raises `ValueError` |
| `test_devto_tags_truncated_at_4` | 6 tags passed → only first 4 sent, warning logged |
| `test_devto_write_publish_log_on_success` | publish_log written with status=success |
| `test_devto_write_publish_log_on_failure` | publish_log written with status=failed |
| `test_devto_retry_on_500` | Mock 500 → 500 → 201, succeeds on third attempt |
| `test_devto_no_retry_on_401` | Mock 401, fails immediately |
| `test_devto_idempotency_returns_existing` | Existing success in publish_log → returns existing, no HTTP call |
| `test_devto_update_article` | Mock PUT → 200, returns updated devto_url |

### `tests/test_idempotency.py` — 3 tests

| Test | Behaviour |
|---|---|
| `test_wp_idempotency_no_duplicate_log` | Two create_post calls → only one publish_log success row (ON CONFLICT IGNORE) |
| `test_devto_idempotency_no_duplicate_log` | Two create_article calls → only one publish_log success row |
| `test_idempotency_failed_then_success` | Failed log exists → retry succeeds → success row written, failed row preserved |

**Target floor: 60 passing, 0 failing, 0 skipped**
(37 existing + 10 WP + 10 Dev.to + 3 idempotency)

> ⚠️ RULE: All HTTP calls mocked via `pytest-httpx` or `unittest.mock`. No real network calls. No real WordPress. No real Dev.to.

> ⚠️ RULE: SQLite operations use in-memory DB from conftest.py `db` fixture. publish_log table must be present in fixture schema.

---

## §4 Completion Criteria

- [ ] pytest reports **60 passing, 0 failing, 0 skipped**
- [ ] `WordPressHandler.create_post` checks idempotency before HTTP call
- [ ] `DevToHandler.create_article` raises `ValueError` if canonical_url is None or empty
- [ ] Both handlers write to publish_log on success and failure
- [ ] Retry logic uses BaseAPIHandler — not reimplemented
- [ ] `WordPressAPIError` and `DevToAPIError` defined in respective files
- [ ] Dev.to tags truncated at 4, warning logged, no exception raised
- [ ] Default publish status is `"draft"` for both handlers
- [ ] `docs/state/current.md` updated to Phase 3 complete

---

## §5 Quick Reference

| Key | Value |
|---|---|
| Certified floor entering | 37/0/0 |
| Target floor exiting | 60/0/0 |
| New tests | 23 (10 WP + 10 Dev.to + 3 idempotency) |
| New files | 2 handlers + 3 test files |
| WP endpoint | `{WP_URL}/wp-json/wp/v2/posts` |
| WP auth | HTTP Basic (user, app_password) |
| Dev.to endpoint | `https://dev.to/api/articles` |
| Dev.to auth | Header `api-key: {DEVTO_API_KEY}` |
| Dev.to tag limit | 4 max — truncate silently, log warning |
| Default status | `"draft"` for both handlers |
| Idempotency check | publish_log query before every create call |
| Retry attempts | Max 4, exponential backoff 2s/4s/8s |
| No retry on | 401, 400 |
| Network in tests | Zero — all mocked |
| Deferred | Publisher orchestration, approval gate, MCP tools |

---

*rfd-blog-engine Phase 3 Directive | June 2026 | RFD IT Services Ltd.*
*Director → Pipeline → Agent. Spec first. Test floor always real.*

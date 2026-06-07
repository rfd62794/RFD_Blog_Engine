# rfd-blog-engine — Patch Directive: Scheduled Publishing

*June 2026 | Read fully before executing anything.*

---

> ⛔ **STOP:** Run pytest before touching any file.
> Must report **121 passing, 0 failing, 0 skipped**.
> If count differs, stop and report — do not proceed.

---

## §0 Context

**What this patch delivers:**
One new optional parameter — `scheduled_date` — added to `publish_to_wordpress` in both the API handler and the MCP tool. When provided, the post is created with `status: future` and the given date. When omitted, behavior is unchanged.

**What is NOT in scope:**
- Any other tools or files
- Dev.to scheduling (deferred)
- Any refactoring

---

## §1 Scope Statement

| File | Status | Action |
|---|---|---|
| `blog_engine/api/wordpress.py` | Modify | Add `scheduled_date` param to `create_post` |
| `blog_engine/tools/publish_tools.py` | Modify | Add `scheduled_date` param to `publish_to_wordpress` tool |
| `tests/test_wordpress.py` | Modify | Add 2 new tests for scheduled publish |
| All other files | Read-only | Do not touch. |

---

## §2 Implementation

### `blog_engine/api/wordpress.py` — `create_post` method

Add `scheduled_date: str = None` parameter.

When `scheduled_date` is provided:
- Set `status` to `"future"` regardless of the `status` parameter passed
- Include `date` field in the POST body: `"date": scheduled_date`
- Format must be ISO 8601: `"2026-06-14T09:00:00"`

When `scheduled_date` is None: behavior unchanged.

> ⚠️ RULE: `scheduled_date` overrides `status` — if a date is provided, status is always `"future"`. Do not allow `status="publish"` with a future date.

---

### `blog_engine/tools/publish_tools.py` — `publish_to_wordpress` tool

Add `scheduled_date: str = None` parameter.

```python
async def publish_to_wordpress(
    post_id: str,
    publish: bool = False,
    scheduled_date: str = None  # ISO 8601: "2026-06-14T09:00:00"
) -> dict:
    """
    Publish approved draft to WordPress.
    Draft must have status: approved.
    publish=False creates WP draft.
    publish=True publishes immediately.
    scheduled_date="2026-06-14T09:00:00" schedules for future publish.
    scheduled_date overrides publish parameter when provided.
    Returns: {post_id, wp_post_id, wp_url, status}
    On error: {"error": str(e), "post_id": post_id}
    """
```

Pass `scheduled_date` through to `publisher.publish_wordpress()` and on to `wp_handler.create_post()`.

> ⚠️ RULE: Update `publisher.py` `publish_wordpress` method signature to accept and pass through `scheduled_date`. One additional parameter, nothing else changes.

---

## §3 Test Anchors

Add to `tests/test_wordpress.py`:

| Test | Behaviour |
|---|---|
| `test_wp_scheduled_post_uses_future_status` | Mock POST with scheduled_date → request body contains `status: future` and `date` field |
| `test_wp_scheduled_overrides_publish_param` | publish=True + scheduled_date → status is still `future` not `publish` |

**Target floor: 123 passing, 0 failing, 0 skipped**
(121 existing + 2 new)

> ⚠️ RULE: No network calls. Mock only.
> ⚠️ RULE: asyncio.run() pattern. No pytest-asyncio. ADR-010.

---

## §4 Completion Criteria

- [ ] pytest reports **123 passing, 0 failing, 0 skipped**
- [ ] `scheduled_date` parameter present in tool, publisher, and handler
- [ ] Scheduled post uses `status: future` in WP API call
- [ ] `scheduled_date` overrides `publish` parameter
- [ ] Existing publish behavior unchanged when `scheduled_date` is None
- [ ] `docs/state/current.md` updated

---

## §5 Quick Reference

| Key | Value |
|---|---|
| Certified floor entering | 121/0/0 |
| Target floor exiting | 123/0/0 |
| New tests | 2 |
| Modified files | `wordpress.py`, `publish_tools.py`, `publisher.py`, `test_wordpress.py` |
| Date format | ISO 8601: `"2026-06-14T09:00:00"` |
| Status when scheduled | Always `"future"` |
| Network in tests | Zero |
| pytest-asyncio | Not used — ADR-010 |

---

*rfd-blog-engine Patch Directive | June 2026 | RFD IT Services Ltd.*

# rfd-blog-engine — Phase 2 Directive: Draft Manager

*June 2026 | Read fully before executing anything.*

---

> ⛔ **STOP:** Run pytest before touching any file.
> Must report **20 passing, 0 failing, 0 skipped**.
> If count differs, stop and report — do not proceed.

---

## §0 Context

**What exists:**
Phase 1 complete. 20/20/0 certified floor. Repo structure, borrowed infra files, SQLite schema with all tables and indexes, inventory.yaml seeded with 5 posts, structlog logger, .env.example. All tests passing.

**What this phase delivers:**
`draft_manager.py` — the core module for JSON draft CRUD operations and SQLite context storage. All draft lifecycle operations: create, read, update, delete, approve. Revision history: save, get, revert. Post context frame slot storage. Six new MCP-facing functions, fully tested.

**Why it matters:**
Every publish path — internal generation and external Claude authoring — converges at a draft JSON. Draft Manager is the single module that owns draft state. Nothing publishes without passing through here first.

**What is NOT in scope:**
- MCP tool registration (Phase 5)
- API handlers for WordPress or Dev.to (Phase 3)
- Model router or generation (Phase 4)
- Approval gate enforcement on publish (Phase 6)
- Inventory status updates (Phase 5)
- Any network calls whatsoever

---

## §1 Scope Statement

| File | Status | Action |
|---|---|---|
| `blog_engine/core/draft_manager.py` | New | Full draft CRUD + revision + context |
| `tests/test_draft_manager.py` | New | 15 new tests |
| `docs/state/current.md` | Modify | Update to Phase 2 complete on finish |
| `blog_engine/infra/base_api_handler.py` | Read-only | Do not touch. |
| `blog_engine/infra/db_manager.py` | Read-only | Do not touch. |
| `blog_engine/infra/cache_manager.py` | Read-only | Do not touch. |
| `blog_engine/infra/model_router.py` | Read-only | Do not touch. |
| `blog_engine/infra/logger.py` | Read-only | Do not touch. |
| `data/inventory.yaml` | Read-only | Do not touch. |
| `tests/test_db_manager.py` | Read-only | Do not touch. |
| `tests/test_inventory.py` | Read-only | Do not touch. |
| `tests/test_env.py` | Read-only | Do not touch. |

**Read-only — do not touch:**
`base_api_handler.py`, `db_manager.py`, `cache_manager.py`, `model_router.py`, `logger.py`, `inventory.yaml`, all existing test files.

Report before fixing any bug found in read-only files. Do not silently modify out-of-scope files.

---

## §2 Implementation

### `blog_engine/core/draft_manager.py`

Single class `DraftManager` with a `DBManager` dependency injected at init. All draft JSON files live in `data/drafts/`. All context and revision data lives in SQLite.

```python
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
import json

from blog_engine.infra.db_manager import DBManager
from blog_engine.infra.logger import get_logger

DRAFTS_DIR = Path("data/drafts")
VALID_STATUSES = {"draft", "approved", "published"}
VALID_TAG_SOURCES = {"auto", "manual", "per_post"}

class DraftManager:
    def __init__(self, db: DBManager):
        self.db = db
        self.logger = get_logger(__name__)
        DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

    # --- Draft CRUD ---
    def create_draft(
        self,
        post_id: str,
        title: str,
        content: str,
        tags: list[str] = [],
        categories: list[str] = [],
        tags_source: str = "manual",
        categories_source: str = "manual",
        generation_source: str = "external"
    ) -> dict: ...

    def get_draft(self, post_id: str) -> Optional[dict]: ...

    def update_draft(
        self,
        post_id: str,
        content: str,
        saved_by: str = "human"
    ) -> dict: ...

    def approve_draft(
        self,
        post_id: str,
        approved_by: str = "human"
    ) -> dict: ...

    def delete_draft(self, post_id: str) -> bool: ...

    # --- Revision history ---
    def save_revision(
        self,
        post_id: str,
        content: str,
        saved_by: str = "human"
    ) -> int: ...  # returns revision_number

    def get_revision_history(self, post_id: str) -> list[dict]: ...

    def revert_revision(
        self,
        post_id: str,
        revision_number: int
    ) -> dict: ...  # returns updated draft

    # --- Context (frame slots) ---
    def save_context(
        self,
        post_id: str,
        raw_extraction: str = None,
        frame_moment: str = None,
        frame_surprise: str = None,
        frame_struggle: str = None,
        frame_lesson: str = None,
        frame_next: str = None,
        related_posts: list[str] = []
    ) -> None: ...

    def get_context(self, post_id: str) -> Optional[dict]: ...
```

> ⚠️ RULE: `create_draft` raises `ValueError` if a draft JSON already exists for `post_id`. Never silently overwrite an existing draft.

> ⚠️ RULE: `update_draft` calls `save_revision` before writing the new content. Revision is saved first. If revision save fails, update does not proceed.

> ⚠️ RULE: `approve_draft` raises `ValueError` if draft `status` is not `"draft"`. Cannot approve an already-approved or published draft.

> ⚠️ RULE: `delete_draft` removes the JSON file and all SQLite context and revision records for the post_id. It does NOT touch inventory.yaml — that is Phase 5 scope.

> ⚠️ RULE: `revert_revision` saves the current content as a new revision before overwriting with the reverted content. Revert is non-destructive.

> ⚠️ RULE: All draft JSON writes use atomic write pattern: write to `{post_id}.tmp`, then rename to `{post_id}.json`. Never write directly to the final path.

> ⚠️ RULE: `tags_source` and `categories_source` must be one of `{"auto", "manual", "per_post"}`. Raise `ValueError` on invalid value.

> ⚠️ RULE: `generation_source` must be one of `{"internal", "external"}`. Raise `ValueError` on invalid value.

**Draft JSON written by `create_draft`:**
```json
{
  "post_id": "dev-001",
  "title": "...",
  "status": "draft",
  "content": "...",
  "excerpt": "",
  "tags": [],
  "categories": [],
  "tags_source": "manual",
  "categories_source": "manual",
  "created_at": "2026-06-07T11:00:00+00:00",
  "updated_at": "2026-06-07T11:00:00+00:00",
  "approved_at": null,
  "approved_by": null,
  "wp_post_id": null,
  "wp_url": null,
  "devto_id": null,
  "devto_url": null,
  "published_at": null,
  "revision_count": 0,
  "generation_source": "external"
}
```

All timestamps use `datetime.now(timezone.utc).isoformat()`.

---

## §3 Test Anchors

| Test | Target file | Behaviour |
|---|---|---|
| `test_create_draft_success` | `draft_manager.py` | Creates draft JSON, returns dict with correct fields |
| `test_create_draft_duplicate_raises` | `draft_manager.py` | Raises `ValueError` if draft already exists |
| `test_get_draft_returns_dict` | `draft_manager.py` | Returns parsed draft for existing post_id |
| `test_get_draft_missing_returns_none` | `draft_manager.py` | Returns `None` for unknown post_id |
| `test_update_draft_saves_revision_first` | `draft_manager.py` | Revision saved before content updated |
| `test_update_draft_increments_revision_count` | `draft_manager.py` | `revision_count` increments on each update |
| `test_approve_draft_sets_status` | `draft_manager.py` | Status changes to `approved`, `approved_at` set |
| `test_approve_draft_already_approved_raises` | `draft_manager.py` | Raises `ValueError` on double-approve |
| `test_delete_draft_removes_file` | `draft_manager.py` | JSON file deleted from data/drafts/ |
| `test_delete_draft_clears_sqlite` | `draft_manager.py` | Revisions and context removed from SQLite |
| `test_save_revision_increments` | `draft_manager.py` | Second save produces revision_number 2 |
| `test_get_revision_history_ordered` | `draft_manager.py` | Returns revisions in ascending revision_number order |
| `test_revert_revision_saves_current_first` | `draft_manager.py` | Current content saved as new revision before revert |
| `test_revert_revision_restores_content` | `draft_manager.py` | Draft content matches reverted revision after revert |
| `test_save_and_get_context` | `draft_manager.py` | Frame slots saved and retrieved correctly |

**Target floor: 35 passing, 0 failing, 0 skipped**
(20 existing + 15 new)

> ⚠️ RULE: All tests use in-memory SQLite via the `db` fixture from conftest.py. No file system side effects from SQLite. Draft JSON files written to a temp directory fixture, cleaned up after each test.

> ⚠️ RULE: No network calls. No external APIs. No model router. Pure file system and SQLite operations only.

---

## §4 Completion Criteria

- [ ] pytest reports **35 passing, 0 failing, 0 skipped**
- [ ] `draft_manager.py` implements all 9 public methods with correct signatures
- [ ] Atomic write pattern used for all draft JSON writes (write to .tmp, rename)
- [ ] `create_draft` raises `ValueError` on duplicate post_id
- [ ] `approve_draft` raises `ValueError` on non-draft status
- [ ] `revert_revision` saves current content before reverting
- [ ] `delete_draft` removes both JSON file and all SQLite records
- [ ] All enum validations raise `ValueError` on invalid input
- [ ] `docs/state/current.md` updated to Phase 2 complete

---

## §5 Quick Reference

| Key | Value |
|---|---|
| Certified floor entering | 20/0/0 |
| Target floor exiting | 35/0/0 |
| New tests | 15 |
| New files | 1 (`draft_manager.py`) + 1 (`test_draft_manager.py`) |
| Draft JSON location | `data/drafts/{post_id}.json` |
| Atomic write pattern | Write to `{post_id}.tmp`, rename to `{post_id}.json` |
| Valid status values | `draft`, `approved`, `published` |
| Valid tags_source values | `auto`, `manual`, `per_post` |
| Valid generation_source values | `internal`, `external` |
| SQLite tables written | `draft_revisions`, `post_context` |
| SQLite tables NOT written | `publish_log`, `post_threads` (Phase 6 and 5) |
| Network calls | None — zero external calls in this phase |
| Deferred | Inventory status update, MCP tool registration, publish log |

---

*rfd-blog-engine Phase 2 Directive | June 2026 | RFD IT Services Ltd.*
*Director → Pipeline → Agent. Spec first. Test floor always real.*

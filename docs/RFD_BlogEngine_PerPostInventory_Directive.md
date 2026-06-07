# RFD_Blog_Engine — Phase 2 Directive: Per-Post Inventory + register_post Tool

*June 2026 | Read fully before executing anything.*

---

> ⛔ **STOP:** Run `uv run pytest` before touching any file.
> Record the exact output line: `X passed, Y failed, Z skipped`.
> If any tests are failing, stop and report — do not proceed until the floor is clean.

---

## §0 Context

### What exists
The blog engine uses a monolithic `data/inventory.yaml` to register all posts. `InventoryManager` reads and writes this single file. Every `publish_to_wordpress` call ends with `inventory.update_status(post_id, "published")` — which fails with `ValueError("Post not found")` if the post wasn't manually added to `inventory.yaml` first. There is no MCP tool to register new posts. Today's workaround required direct filesystem edits mid-session.

### What this phase delivers
1. **Per-post YAML files** — `data/inventory/{post_id}.yaml`, one file per post. `InventoryManager` scans the directory instead of reading one file. No more merge conflicts, no more manual appending.
2. **`register_post` MCP tool** — Creates a new per-post YAML file. Closes the gap that required filesystem workarounds.
3. **`scheduled_date` field** — Optional field on per-post YAML. `publish_to_wordpress` tool reads it as a fallback when no date is passed explicitly.
4. **Migration** — Existing 7 posts (dev-001 through dev-007) moved to individual files. `inventory.yaml` retired.
5. **Test suite updated** — `conftest.py` fixture and `test_inventory.py` updated for directory-based `InventoryManager`.

### What is NOT in scope
- `publisher.py` — no changes
- `draft_manager.py` — no changes
- `generator.py` — no changes
- `api/wordpress.py`, `api/devto.py` — no changes
- `server.py` — no changes
- Any test file other than `conftest.py` and `test_inventory.py`
- Dev.to scheduled_date support (not needed, deferred)

---

## §1 Scope

| File | Status | Action |
|---|---|---|
| `blog_engine/core/inventory.py` | Modify | Full refactor: dir-based scan, `add_post()`, updated write paths |
| `blog_engine/tools/draft_tools.py` | Modify | Add `register_post` tool, register with mcp |
| `blog_engine/tools/publish_tools.py` | Modify | Add `scheduled_date` fallback from inventory |
| `tests/conftest.py` | Modify | Update `inventory` fixture for dir-based InventoryManager |
| `tests/test_inventory.py` | Modify | Rewrite tests for dir-based InventoryManager, add `add_post` tests |
| `data/inventory/` | New (dir) | Create directory |
| `data/inventory/dev-001.yaml` | New | Migrated from inventory.yaml |
| `data/inventory/dev-002.yaml` | New | Migrated from inventory.yaml |
| `data/inventory/dev-003.yaml` | New | Migrated from inventory.yaml |
| `data/inventory/dev-004.yaml` | New | Migrated from inventory.yaml |
| `data/inventory/dev-005.yaml` | New | Migrated from inventory.yaml |
| `data/inventory/dev-006.yaml` | New | Migrated from inventory.yaml |
| `data/inventory/dev-007.yaml` | New | Migrated from inventory.yaml |
| `data/inventory.yaml` | Retire | Rename to `data/inventory.yaml.bak` after migration verified |

**Read-only — do not touch:**
`publisher.py`, `draft_manager.py`, `generator.py`, `server.py`,
`api/wordpress.py`, `api/devto.py`, `blog_engine/infra/`,
all test files except `conftest.py` and `test_inventory.py`

> ⚠️ RULE: If a file is not in the scope table above, do not touch it. Report before fixing any bug found in a read-only file.

---

## §2 Implementation

### 2a — Per-post YAML schema

Every file in `data/inventory/` uses this schema. All fields except `scheduled_date` are required.

```yaml
post_id: dev-008
title: "Post title here"
status: pending
category: ai-methodology
notes: |
  What the post is about.
  Frame slots: MOMENT (...), SURPRISE (...), STRUGGLE (...), LESSON (...), NEXT (...)
tags:
  - tag1
  - tag2
scheduled_date: "2026-07-19T09:00:00"   # optional — ISO 8601 local time
created_at: "2026-06-07T23:00:00"
```

Valid statuses (unchanged): `pending`, `drafted`, `approved`, `published`

---

### 2b — `blog_engine/core/inventory.py`

Full replacement. Keep the same public interface — all callers continue to work unchanged.

> ⚠️ RULE: The public method signatures for `load()`, `get_post()`, `list_by_status()`, `update_status()`, and `get_context_for_generation()` must not change. Only the internal implementation changes.

```python
"""
blog_engine/core/inventory.py

Per-post YAML inventory manager.
Scans data/inventory/ directory — one YAML file per post.
"""

from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
import yaml

from blog_engine.infra.logger import get_logger

INVENTORY_DIR = Path(__file__).parent.parent.parent / "data" / "inventory"
VALID_STATUSES = {"pending", "drafted", "approved", "published"}


class InventoryManager:
    def __init__(self, inventory_dir: Path = INVENTORY_DIR):
        self.inventory_dir = inventory_dir
        self.inventory_dir.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger(__name__)

    def load(self) -> list[dict]:
        """Load all posts by scanning inventory_dir/*.yaml. Returns list of post dicts."""
        posts = []
        for path in sorted(self.inventory_dir.glob("*.yaml")):
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data and "post_id" in data:
                posts.append(data)
        return posts

    def get_post(self, post_id: str) -> Optional[dict]:
        """Return single post by post_id. Returns None if not found."""
        path = self.inventory_dir / f"{post_id}.yaml"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def list_by_status(self, status: str) -> list[dict]:
        """Return posts filtered by status. Raises ValueError on invalid status."""
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}. Must be one of {VALID_STATUSES}")
        return [p for p in self.load() if p.get("status") == status]

    def update_status(self, post_id: str, status: str) -> None:
        """
        Update status field for a post.
        Atomic write to individual YAML file.
        Raises ValueError if post_id not found or status invalid.
        """
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}. Must be one of {VALID_STATUSES}")

        path = self.inventory_dir / f"{post_id}.yaml"
        if not path.exists():
            raise ValueError(f"Post not found: {post_id}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        data["status"] = status

        tmp_path = path.with_suffix(".yaml.tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
        tmp_path.replace(path)

        self.logger.info("inventory.status_updated", post_id=post_id, status=status)

    def add_post(
        self,
        post_id: str,
        title: str,
        category: str,
        notes: str,
        tags: list,
        scheduled_date: str = None
    ) -> dict:
        """
        Create a new per-post YAML file.
        Raises ValueError if post_id already exists.
        Returns the new post dict.
        """
        path = self.inventory_dir / f"{post_id}.yaml"
        if path.exists():
            raise ValueError(f"Post already exists: {post_id}")

        data = {
            "post_id": post_id,
            "title": title,
            "status": "pending",
            "category": category,
            "notes": notes,
            "tags": tags,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if scheduled_date is not None:
            data["scheduled_date"] = scheduled_date

        tmp_path = path.with_suffix(".yaml.tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
        tmp_path.replace(path)

        self.logger.info("inventory.post_added", post_id=post_id, title=title)
        return data

    def get_context_for_generation(self, post_id: str) -> dict:
        """
        Returns dict with all fields needed for prompt construction.
        Raises KeyError if post_id not found.
        """
        post = self.get_post(post_id)
        if not post:
            raise KeyError(f"Post not found: {post_id}")

        return {
            "post_id": post["post_id"],
            "title": post.get("title", ""),
            "category": post.get("category", ""),
            "notes": post.get("notes", ""),
            "tags": post.get("tags", []),
            "status": post.get("status", "pending"),
            "scheduled_date": post.get("scheduled_date"),
        }
```

---

### 2c — `blog_engine/tools/draft_tools.py`

Add `register_post` function and register it with mcp. Insert before `register_draft_tools`. All existing functions are unchanged.

> ⚠️ RULE: Do not modify any existing function in this file. Only add `register_post` and update `register_draft_tools` to include it.

```python
async def register_post(
    post_id: str,
    title: str,
    category: str,
    notes: str,
    tags: list,
    scheduled_date: str = None
) -> dict:
    """
    Register a new post in the inventory.
    Creates data/inventory/{post_id}.yaml with status: pending.
    Raises if post_id already exists.
    Returns the new post dict.
    scheduled_date: optional ISO 8601 string e.g. "2026-07-19T09:00:00"
    """
    try:
        inventory = InventoryManager()
        return inventory.add_post(
            post_id=post_id,
            title=title,
            category=category,
            notes=notes,
            tags=tags,
            scheduled_date=scheduled_date
        )
    except Exception as e:
        logger.error("register_post.error", post_id=post_id, error=str(e))
        return {"error": str(e), "post_id": post_id}
```

Update `register_draft_tools`:
```python
def register_draft_tools(mcp):
    """Register draft management tools with FastMCP server."""
    mcp.tool()(register_post)       # ← add this line
    mcp.tool()(list_inventory)
    mcp.tool()(get_draft)
    mcp.tool()(create_draft)
    mcp.tool()(update_draft)
    mcp.tool()(approve_draft)
    mcp.tool()(delete_draft)
    mcp.tool()(revert_revision)
    mcp.tool()(get_revision_history)
```

Add `InventoryManager` import at top of file (it's already imported in some tools — confirm it's present):
```python
from blog_engine.core.inventory import InventoryManager
```

---

### 2d — `blog_engine/tools/publish_tools.py`

Add `scheduled_date` fallback in `publish_to_wordpress`. No other changes to this file.

> ⚠️ RULE: Only modify the `publish_to_wordpress` function. Do not touch any other function.

Replace the `publish_to_wordpress` function body with:

```python
async def publish_to_wordpress(post_id: str, publish: bool = False, scheduled_date: str = None) -> dict:
    """
    Publish approved draft to WordPress.
    Draft must have status: approved. Calls approval gate.
    publish=False creates WP draft. publish=True publishes immediately.
    scheduled_date="2026-06-14T09:00:00" schedules for future publish.
    If scheduled_date not provided, falls back to scheduled_date from inventory YAML.
    scheduled_date overrides publish parameter when provided.
    Returns: {post_id, wp_post_id, wp_url, status}
    On error: {"error": str(e), "post_id": post_id}
    """
    try:
        # Fallback: read scheduled_date from inventory if not explicitly passed
        if scheduled_date is None:
            try:
                inventory = InventoryManager()
                post = inventory.get_post(post_id)
                if post:
                    scheduled_date = post.get("scheduled_date")
            except Exception:
                pass  # Fallback gracefully — inventory lookup failure is non-fatal

        publisher = _get_publisher()
        return await publisher.publish_wordpress(post_id, publish=publish, scheduled_date=scheduled_date)
    except Exception as e:
        logger.error("publish_to_wordpress.error", post_id=post_id, error=str(e))
        return {"error": str(e), "post_id": post_id}
```

Add `InventoryManager` import at top if not already present:
```python
from blog_engine.core.inventory import InventoryManager
```

---

### 2e — Migration: data/inventory/

Create `data/inventory/` directory. Write one YAML file per existing post using the schema from §2a.

Read the current `data/inventory.yaml`, extract each post entry, and write it to `data/inventory/{post_id}.yaml`. Use `scheduled_date` from the actual WordPress schedule for posts that are already published/scheduled.

Migration data (write exactly as shown):

**dev-001.yaml:**
```yaml
post_id: dev-001
title: I built the same game for 20 years without knowing it
status: published
category: developer-identity
notes: |
  The voiddrift realization. Every game I've made is the same loop.
  Frame slots: MOMENT (the realization), SURPRISE (it was always there),
  STRUGGLE (why I didn't see it), LESSON (patterns are invisible to the creator),
  NEXT (lean into the pattern instead of fighting it).
tags:
  - identity
  - voiddrift
  - origin
created_at: '2026-06-07T11:00:00'
```

**dev-002.yaml:**
```yaml
post_id: dev-002
title: Why I stopped optimizing for engagement
status: published
category: content-strategy
notes: |
  The YouTube metrics trap. Views don't equal impact.
  Frame slots: MOMENT (burnout from chasing views), SURPRISE (quality over quantity),
  STRUGGLE (algorithm pressure), LESSON (make for one person, not everyone),
  NEXT (ignore analytics, focus on craft).
tags:
  - youtube
  - strategy
  - burnout
created_at: '2026-06-07T11:00:00'
```

**dev-003.yaml:**
```yaml
post_id: dev-003
title: 'The PrivyBot architecture: why MCP matters'
status: published
category: technical
notes: |
  Model Context Protocol as the future of agent-tool integration.
  Frame slots: MOMENT (MCP clicked), SURPRISE (it's not just another API),
  STRUGGLE (building the tool layer), LESSON (tools are the interface, not the model),
  NEXT (standardize tool contracts across all agents).
tags:
  - mcp
  - architecture
  - privybot
created_at: '2026-06-07T11:00:00'
```

**dev-004.yaml:**
```yaml
post_id: dev-004
title: Spec-Driven Development saved my project
status: published
category: methodology
notes: |
  Writing the SDD before code. The floor metric discipline.
  Frame slots: MOMENT (adr-001 decision), SURPRISE (spec prevents scope creep),
  STRUGGLE (resistance to writing docs first), LESSON (spec is code, just declarative),
  NEXT (SDD-first for all future projects).
tags:
  - sdd
  - methodology
  - planning
created_at: '2026-06-07T11:00:00'
```

**dev-005.yaml:**
```yaml
post_id: dev-005
title: Borrowing code vs. reinventing the wheel
status: published
category: technical
notes: |
  The PrivyBot infra files copied to rfd-blog-engine.
  Frame slots: MOMENT (copying base_api_handler), SURPRISE (divergence is intentional),
  STRUGGLE (sync strategy question), LESSON (copy now, sync later if needed),
  NEXT (document divergence, don't over-engineer sync).
tags:
  - infrastructure
  - code-reuse
  - privybot
created_at: '2026-06-07T11:00:00'
```

**dev-006.yaml:**
```yaml
post_id: dev-006
title: The Agent Told Me It Was Done. The Tests Said Otherwise.
status: published
category: ai-methodology
notes: |
  Coding agent fabrication and the proof standard. pytest floor discipline.
  Frame slots: MOMENT (agent reports passing, terminal says otherwise),
  SURPRISE (agents predict summaries, not read truth),
  STRUGGLE (trusting summaries across sessions),
  LESSON (raw terminal output only — summary is a prediction),
  NEXT (stop rules and SDD directive structure).
tags:
  - ai
  - coding-agents
  - testing
  - spec-driven-development
  - windsurf
scheduled_date: '2026-07-05T09:00:00'
created_at: '2026-06-07T23:00:00'
```

**dev-007.yaml:**
```yaml
post_id: dev-007
title: I Processed 671,000 Records in 6 Minutes and 32 Seconds
status: published
category: data-engineering
notes: |
  Brownbook ETL pipeline. 12-step lead data processing at scale.
  Frame slots: MOMENT (BOM file breaks column parsing at 9am),
  SURPRISE (EF BB BF — three invisible bytes in the header),
  STRUGGLE (one-off tools accumulating without a contract),
  LESSON (Golden Columns as canonical schema converts tools to stages),
  NEXT (the pipeline is the design, not the improvisation).
tags:
  - data-engineering
  - python
  - etl
  - automation
  - lead-data
  - performance
  - pipeline
scheduled_date: '2026-07-12T09:00:00'
created_at: '2026-06-07T23:20:00'
```

After all 7 files are written and verified, rename `data/inventory.yaml` → `data/inventory.yaml.bak`.

---

### 2f — `tests/conftest.py`

Replace the `inventory` fixture only. All other fixtures unchanged.

> ⚠️ RULE: Only replace the `inventory` fixture. Do not touch `temp_dir`, `db`, or `draft` fixtures.

```python
@pytest.fixture
def inventory(temp_dir):
    """Temporary inventory directory with test posts (per-post YAML files)."""
    import yaml

    inventory_dir = temp_dir / "inventory"
    inventory_dir.mkdir(parents=True, exist_ok=True)

    posts = [
        {
            "post_id": "test-001",
            "title": "Test Post 1",
            "status": "pending",
            "category": "test",
            "notes": "Test notes for frame extraction",
            "tags": ["test", "fixture"],
            "created_at": "2026-06-07T11:00:00",
        },
        {
            "post_id": "test-002",
            "title": "Test Post 2",
            "status": "drafted",
            "category": "test",
            "notes": "Another test post",
            "tags": ["test"],
            "created_at": "2026-06-07T11:00:00",
        },
    ]

    for post in posts:
        path = inventory_dir / f"{post['post_id']}.yaml"
        with open(path, "w") as f:
            yaml.safe_dump(post, f, sort_keys=False)

    return inventory_dir  # returns Path to directory, not file
```

---

### 2g — `tests/test_inventory.py`

Full replacement. Tests must cover the new directory-based interface and `add_post`.

> ⚠️ RULE: Write all tests from scratch against the new interface. Do not attempt to preserve old test logic that references `inventory.yaml` as a file.

```python
"""
tests/test_inventory.py

Tests for per-post YAML inventory (directory-based InventoryManager).
"""

import pytest
import yaml
from pathlib import Path
from blog_engine.core.inventory import InventoryManager


def test_inventory_loads(inventory):
    """InventoryManager.load() returns all posts from directory."""
    manager = InventoryManager(inventory)
    posts = manager.load()
    assert len(posts) == 2
    ids = {p["post_id"] for p in posts}
    assert ids == {"test-001", "test-002"}


def test_inventory_post_schema(inventory):
    """Each post has all required fields."""
    manager = InventoryManager(inventory)
    posts = manager.load()
    required_fields = ["post_id", "title", "status", "category", "notes", "tags", "created_at"]
    for post in posts:
        for field in required_fields:
            assert field in post, f"Missing field '{field}' in post {post.get('post_id')}"


def test_inventory_status_values(inventory):
    """All posts have valid status values."""
    manager = InventoryManager(inventory)
    valid_statuses = {"pending", "drafted", "approved", "published"}
    for post in manager.load():
        assert post["status"] in valid_statuses


def test_inventory_tags_are_list(inventory):
    """Tags field is a list on all posts."""
    manager = InventoryManager(inventory)
    for post in manager.load():
        assert isinstance(post["tags"], list)


def test_get_post_returns_correct_post(inventory):
    """get_post() returns the correct post by post_id."""
    manager = InventoryManager(inventory)
    post = manager.get_post("test-001")
    assert post is not None
    assert post["post_id"] == "test-001"
    assert post["title"] == "Test Post 1"


def test_get_post_returns_none_for_unknown(inventory):
    """get_post() returns None for unknown post_id."""
    manager = InventoryManager(inventory)
    assert manager.get_post("does-not-exist") is None


def test_list_by_status_filters_correctly(inventory):
    """list_by_status() returns only posts matching status."""
    manager = InventoryManager(inventory)
    pending = manager.list_by_status("pending")
    assert len(pending) == 1
    assert pending[0]["post_id"] == "test-001"

    drafted = manager.list_by_status("drafted")
    assert len(drafted) == 1
    assert drafted[0]["post_id"] == "test-002"


def test_list_by_status_invalid_raises(inventory):
    """list_by_status() raises ValueError on invalid status."""
    manager = InventoryManager(inventory)
    with pytest.raises(ValueError, match="Invalid status"):
        manager.list_by_status("invalid_status")


def test_update_status_writes_to_file(inventory):
    """update_status() persists the change to the individual YAML file."""
    manager = InventoryManager(inventory)
    manager.update_status("test-001", "drafted")
    post = manager.get_post("test-001")
    assert post["status"] == "drafted"


def test_update_status_invalid_raises(inventory):
    """update_status() raises ValueError on invalid status string."""
    manager = InventoryManager(inventory)
    with pytest.raises(ValueError, match="Invalid status"):
        manager.update_status("test-001", "invalid_status")


def test_update_status_unknown_post_raises(inventory):
    """update_status() raises ValueError for unknown post_id."""
    manager = InventoryManager(inventory)
    with pytest.raises(ValueError, match="Post not found"):
        manager.update_status("unknown-999", "drafted")


def test_add_post_creates_file(inventory):
    """add_post() writes a new YAML file to the inventory directory."""
    manager = InventoryManager(inventory)
    result = manager.add_post(
        post_id="test-003",
        title="New Test Post",
        category="test",
        notes="Test notes",
        tags=["new", "test"],
    )
    assert result["post_id"] == "test-003"
    assert result["status"] == "pending"
    assert (inventory / "test-003.yaml").exists()


def test_add_post_with_scheduled_date(inventory):
    """add_post() stores scheduled_date when provided."""
    manager = InventoryManager(inventory)
    manager.add_post(
        post_id="test-004",
        title="Scheduled Post",
        category="test",
        notes="Notes",
        tags=[],
        scheduled_date="2026-08-01T09:00:00",
    )
    post = manager.get_post("test-004")
    assert post["scheduled_date"] == "2026-08-01T09:00:00"


def test_add_post_duplicate_raises(inventory):
    """add_post() raises ValueError if post_id already exists."""
    manager = InventoryManager(inventory)
    with pytest.raises(ValueError, match="Post already exists"):
        manager.add_post(
            post_id="test-001",
            title="Duplicate",
            category="test",
            notes="",
            tags=[],
        )


def test_get_context_for_generation(inventory):
    """get_context_for_generation() returns all required fields."""
    manager = InventoryManager(inventory)
    context = manager.get_context_for_generation("test-001")
    required = ["post_id", "title", "category", "notes", "tags", "status"]
    for field in required:
        assert field in context
    assert context["post_id"] == "test-001"


def test_get_context_unknown_raises(inventory):
    """get_context_for_generation() raises KeyError for unknown post_id."""
    manager = InventoryManager(inventory)
    with pytest.raises(KeyError):
        manager.get_context_for_generation("does-not-exist")


def test_empty_directory_returns_empty_list(temp_dir):
    """load() returns empty list when inventory directory is empty."""
    empty_dir = temp_dir / "empty_inventory"
    empty_dir.mkdir()
    manager = InventoryManager(empty_dir)
    assert manager.load() == []
```

---

## §3 Test Anchors

| Test | File | Behaviour |
|---|---|---|
| `test_inventory_loads` | `test_inventory.py` | `load()` returns 2 posts from directory |
| `test_get_post_returns_correct_post` | `test_inventory.py` | `get_post("test-001")` returns correct dict |
| `test_get_post_returns_none_for_unknown` | `test_inventory.py` | `get_post("does-not-exist")` returns None |
| `test_list_by_status_filters_correctly` | `test_inventory.py` | `list_by_status()` filters by status field |
| `test_update_status_writes_to_file` | `test_inventory.py` | Status persists to individual YAML file |
| `test_update_status_unknown_post_raises` | `test_inventory.py` | `ValueError("Post not found")` for unknown id |
| `test_add_post_creates_file` | `test_inventory.py` | New YAML file written, status=pending |
| `test_add_post_with_scheduled_date` | `test_inventory.py` | `scheduled_date` stored and retrievable |
| `test_add_post_duplicate_raises` | `test_inventory.py` | `ValueError("Post already exists")` on duplicate |
| `test_empty_directory_returns_empty_list` | `test_inventory.py` | Empty dir returns `[]` |

**Target:** All existing passing tests continue to pass. New tests above all pass.

> ⚠️ RULE: Do not delete or skip any existing passing test to make the floor hold. If an existing test breaks due to the refactor, fix the test to match the new interface — do not suppress it.

---

## §4 Completion Criteria

- [ ] `uv run pytest` produces same or higher passing count as pre-flight, 0 failing, 0 skipped (excluding known API-key skips)
- [ ] `data/inventory/` directory exists and contains exactly 7 YAML files (dev-001 through dev-007)
- [ ] `data/inventory.yaml.bak` exists (original file renamed, not deleted)
- [ ] `rfd-blog-engine:list_inventory` (status=published) returns 7 posts via MCP
- [ ] `rfd-blog-engine:register_post` tool is visible in MCP tool list
- [ ] Manual smoke test: `register_post(post_id="smoke-test-001", title="Smoke Test", category="test", notes="Delete me", tags=[], scheduled_date="2026-09-01T09:00:00")` → returns `{post_id: "smoke-test-001", status: "pending", scheduled_date: "2026-09-01T09:00:00"}`
- [ ] Verify `data/inventory/smoke-test-001.yaml` exists on disk
- [ ] Delete `data/inventory/smoke-test-001.yaml` (manual cleanup — not automated)
- [ ] MCP server restarted after changes: `nssm restart RFDBlogEngine` (or equivalent service name)
- [ ] `docs/state/current.md` updated: phase = "Phase 2 — Per-Post Inventory", certified_floor = [real number from pytest]

---

## §5 Quick Reference

| Key | Value |
|---|---|
| Repo | `C:\Github\RFD_Blog_Engine` |
| Runtime | `uv run pytest` |
| Inventory dir | `data/inventory/` |
| Draft dir | `data/drafts/` |
| Per-post YAML schema | `{post_id, title, status, category, notes, tags, created_at, scheduled_date?}` |
| Valid statuses | `pending`, `drafted`, `approved`, `published` |
| New tool | `register_post(post_id, title, category, notes, tags, scheduled_date?)` |
| MCP service | Restart after any changes to `tools/` or `core/` |
| Migration backup | `data/inventory.yaml.bak` |
| Smoke test cleanup | Delete `data/inventory/smoke-test-001.yaml` manually after verification |

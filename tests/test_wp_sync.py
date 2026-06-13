"""
tests/test_wp_sync.py

Tests for blog_engine/tools/wp_sync.py
All WordPress API calls mocked — no network.
"""

import asyncio
import pytest
import yaml
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from blog_engine.tools.wp_sync import (
    get_wordpress_post_by_slug,
    list_wordpress_posts,
    update_inventory_fields,
    import_wordpress_post,
)
from blog_engine.core.inventory import InventoryManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_inventory(tmp_path: Path, posts: list) -> InventoryManager:
    inv_dir = tmp_path / "inventory"
    inv_dir.mkdir(parents=True, exist_ok=True)
    for post in posts:
        path = inv_dir / f"{post['post_id']}.yaml"
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(post, f, sort_keys=False, allow_unicode=True)
    return InventoryManager(inventory_dir=inv_dir)


def _wp_post_raw(wp_id, slug, title="Test Post", status="future", date="2026-10-29T09:00:00"):
    return {
        "id": wp_id,
        "slug": slug,
        "status": status,
        "date": date,
        "title": {"rendered": title},
    }


def _mock_response(data):
    r = MagicMock()
    r.json.return_value = data
    return r


def _mock_wp(response_data):
    """Return a mock WP handler whose _make_request returns response_data."""
    wp = MagicMock()
    wp.base_url = "https://blog.example.com"
    wp.auth = ("user", "pass")
    wp._make_request = AsyncMock(return_value=_mock_response(response_data))
    return wp


# ---------------------------------------------------------------------------
# Test 1 — get_by_slug returns post dict
# ---------------------------------------------------------------------------

def test_get_by_slug_returns_post():
    raw = [_wp_post_raw(118, "zero-wasnt-zero", title="Zero Wasn't Zero", status="future")]
    mock_wp = _mock_wp(raw)

    with patch("blog_engine.tools.wp_sync._get_wp_handler", return_value=mock_wp):
        result = asyncio.run(get_wordpress_post_by_slug("zero-wasnt-zero"))

    assert result["id"] == 118
    assert result["slug"] == "zero-wasnt-zero"
    assert result["title"] == "Zero Wasn't Zero"
    assert result["status"] == "future"

    # Confirm status=any is sent so scheduled posts are visible
    _, kwargs = mock_wp._make_request.call_args
    assert kwargs["params"]["status"] == "any"


# ---------------------------------------------------------------------------
# Test 2 — get_by_slug empty list raises ValueError
# ---------------------------------------------------------------------------

def test_get_by_slug_not_found_raises():
    mock_wp = _mock_wp([])

    with patch("blog_engine.tools.wp_sync._get_wp_handler", return_value=mock_wp):
        with pytest.raises(ValueError, match="No WordPress post found with slug"):
            asyncio.run(get_wordpress_post_by_slug("does-not-exist"))


# ---------------------------------------------------------------------------
# Test 3 — list_posts returns all results, no truncated flag
# ---------------------------------------------------------------------------

def test_list_posts_no_filter():
    raw = [
        _wp_post_raw(1, "post-one"),
        _wp_post_raw(2, "post-two"),
        _wp_post_raw(3, "post-three"),
    ]
    mock_wp = _mock_wp(raw)

    with patch("blog_engine.tools.wp_sync._get_wp_handler", return_value=mock_wp):
        result = asyncio.run(list_wordpress_posts(per_page=100))

    assert len(result) == 3
    assert all("truncated" not in r for r in result)
    assert result[0]["id"] == 1

    # Default must include status=any so scheduled posts are visible
    _, kwargs = mock_wp._make_request.call_args
    assert kwargs["params"]["status"] == "any"


# ---------------------------------------------------------------------------
# Test 4 — list_posts with status filter passes status to WP query
# ---------------------------------------------------------------------------

def test_list_posts_status_filter():
    mock_wp = _mock_wp([_wp_post_raw(115, "some-slug", status="future")])

    with patch("blog_engine.tools.wp_sync._get_wp_handler", return_value=mock_wp):
        asyncio.run(list_wordpress_posts(status="future"))

    call_kwargs = mock_wp._make_request.call_args
    params = call_kwargs.kwargs.get("params") or call_kwargs.args[3] if len(call_kwargs.args) > 3 else {}
    # Extract params from keyword args
    _, kwargs = call_kwargs
    assert kwargs["params"]["status"] == "future"


# ---------------------------------------------------------------------------
# Test 5 — list_posts truncated flag when response == per_page
# ---------------------------------------------------------------------------

def test_list_posts_truncated_flag():
    raw = [_wp_post_raw(i, f"post-{i}") for i in range(3)]
    mock_wp = _mock_wp(raw)

    with patch("blog_engine.tools.wp_sync._get_wp_handler", return_value=mock_wp):
        result = asyncio.run(list_wordpress_posts(per_page=3))

    assert result[-1] == {"truncated": True}
    assert len(result) == 4  # 3 posts + truncated sentinel


# ---------------------------------------------------------------------------
# Test 6 — update_fields writes merged YAML correctly
# ---------------------------------------------------------------------------

def test_update_fields_writes_correctly(tmp_path):
    inventory = _make_inventory(tmp_path, [
        {"post_id": "dev-016", "title": "Zero Wasn't Zero", "status": "published",
         "category": "", "notes": "", "tags": [], "created_at": "2026-06-12T00:00:00"},
    ])

    with patch("blog_engine.tools.wp_sync.InventoryManager", return_value=inventory):
        result = asyncio.run(update_inventory_fields(
            "dev-016",
            {"wp_post_id": 118, "scheduled_date": "2026-06-21T09:00:00"},
        ))

    assert result["wp_post_id"] == 118
    assert result["scheduled_date"] == "2026-06-21T09:00:00"

    # Verify persisted to disk
    with open(inventory.inventory_dir / "dev-016.yaml") as f:
        saved = yaml.safe_load(f)
    assert saved["wp_post_id"] == 118
    assert saved["scheduled_date"] == "2026-06-21T09:00:00"


# ---------------------------------------------------------------------------
# Test 7 — update_fields unknown key raises before touching YAML
# ---------------------------------------------------------------------------

def test_update_fields_unknown_key_raises(tmp_path):
    inventory = _make_inventory(tmp_path, [
        {"post_id": "dev-016", "title": "Test", "status": "published",
         "category": "", "notes": "", "tags": [], "created_at": "2026-06-12T00:00:00"},
    ])
    original_mtime = (inventory.inventory_dir / "dev-016.yaml").stat().st_mtime

    with patch("blog_engine.tools.wp_sync.InventoryManager", return_value=inventory):
        with pytest.raises(ValueError, match="Unknown inventory field"):
            asyncio.run(update_inventory_fields("dev-016", {"devto_id": 99999}))

    # YAML must not have been touched
    assert (inventory.inventory_dir / "dev-016.yaml").stat().st_mtime == original_mtime


# ---------------------------------------------------------------------------
# Test 8 — update_fields unknown post_id raises
# ---------------------------------------------------------------------------

def test_update_fields_unknown_post_raises(tmp_path):
    inventory = _make_inventory(tmp_path, [])

    with patch("blog_engine.tools.wp_sync.InventoryManager", return_value=inventory):
        with pytest.raises(ValueError, match="Post not found in inventory"):
            asyncio.run(update_inventory_fields("dev-999", {"title": "New Title"}))


# ---------------------------------------------------------------------------
# Test 9 — import creates inventory entry with status=imported
# ---------------------------------------------------------------------------

def test_import_creates_inventory_entry(tmp_path):
    inventory = _make_inventory(tmp_path, [])

    mock_wp = MagicMock()
    mock_wp.get_post = AsyncMock(return_value={
        "id": 55,
        "title": {"rendered": "Old Pre-Engine Post"},
        "date": "2025-03-01T09:00:00",
        "status": "publish",
        "slug": "old-pre-engine-post",
    })

    with patch("blog_engine.tools.wp_sync._get_wp_handler", return_value=mock_wp), \
         patch("blog_engine.tools.wp_sync.InventoryManager", return_value=inventory):
        result = asyncio.run(import_wordpress_post(55, "legacy-001"))

    assert result["post_id"] == "legacy-001"
    assert result["wp_post_id"] == 55
    assert result["status"] == "imported"
    assert result["title"] == "Old Pre-Engine Post"
    assert result["scheduled_date"] == "2025-03-01T09:00:00"

    # Verify YAML on disk
    path = inventory.inventory_dir / "legacy-001.yaml"
    assert path.exists()
    with open(path) as f:
        saved = yaml.safe_load(f)
    assert saved["status"] == "imported"
    assert saved["wp_post_id"] == 55


# ---------------------------------------------------------------------------
# Test 10 — import raises if post_id already exists
# ---------------------------------------------------------------------------

def test_import_duplicate_raises(tmp_path):
    inventory = _make_inventory(tmp_path, [
        {"post_id": "dev-001", "title": "Existing", "status": "published",
         "category": "", "notes": "", "tags": [], "created_at": "2026-06-01T00:00:00"},
    ])

    mock_wp = MagicMock()
    mock_wp.get_post = AsyncMock(return_value={"id": 92, "title": {"rendered": "Test"}, "date": "2026-06-07T09:00:00"})

    with patch("blog_engine.tools.wp_sync._get_wp_handler", return_value=mock_wp), \
         patch("blog_engine.tools.wp_sync.InventoryManager", return_value=inventory):
        with pytest.raises(ValueError, match="already exists"):
            asyncio.run(import_wordpress_post(92, "dev-001"))

    mock_wp.get_post.assert_not_called()

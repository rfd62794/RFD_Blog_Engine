"""
tests/test_calendar_tools.py

Tests for blog_engine/tools/calendar.py
All WordPress API calls mocked — no network.
"""

import asyncio
import pytest
import yaml
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from blog_engine.core.inventory import InventoryManager
from blog_engine.tools.calendar import reschedule_post, get_full_calendar


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_inventory(tmp_path: Path, posts: list) -> Path:
    """Write post dicts as YAML files into tmp_path/inventory/. Returns inventory dir."""
    inv_dir = tmp_path / "inventory"
    inv_dir.mkdir(parents=True, exist_ok=True)
    for post in posts:
        path = inv_dir / f"{post['post_id']}.yaml"
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(post, f, sort_keys=False, allow_unicode=True)
    return inv_dir


def _base_post(post_id, title, status="approved", scheduled_date=None, wp_post_id=None):
    p = {
        "post_id": post_id,
        "title": title,
        "status": status,
        "category": "dev",
        "notes": "",
        "tags": [],
        "scheduled_date": scheduled_date,
        "wp_post_id": wp_post_id,
        "created_at": "2026-06-01T00:00:00",
    }
    return p


def _mock_wp_update(return_wp_url="https://blog.example.com/post/"):
    mock = AsyncMock(return_value={"wp_post_id": 99, "wp_url": return_wp_url})
    return mock


# ---------------------------------------------------------------------------
# Test 1 — reschedule sends correct date to WordPress
# ---------------------------------------------------------------------------

def test_reschedule_updates_wordpress_date(tmp_path):
    """Mock WP update_post — verify correct date and status=future sent."""
    inv_dir = _make_inventory(tmp_path, [
        _base_post("dev-020", "Test Post", wp_post_id=119, scheduled_date="2026-09-01T09:00:00"),
    ])

    captured = {}

    async def fake_update_post(post_id, wp_post_id, fields):
        captured["wp_post_id"] = wp_post_id
        captured["fields"] = fields
        return {"wp_post_id": wp_post_id, "wp_url": "https://blog.example.com/post/"}

    mock_wp = MagicMock()
    mock_wp.update_post = fake_update_post

    inventory = InventoryManager(inventory_dir=inv_dir)

    with patch("blog_engine.tools.calendar._get_wp_handler", return_value=mock_wp), \
         patch("blog_engine.tools.calendar.InventoryManager", return_value=inventory):
        result = asyncio.run(reschedule_post("dev-020", "2026-10-29T09:00:00"))

    assert captured["wp_post_id"] == 119
    assert captured["fields"]["date"] == "2026-10-29T09:00:00"
    assert captured["fields"]["status"] == "future"


# ---------------------------------------------------------------------------
# Test 2 — reschedule writes new_date to inventory YAML
# ---------------------------------------------------------------------------

def test_reschedule_updates_inventory_yaml(tmp_path):
    """After reschedule, YAML file on disk has updated scheduled_date."""
    inv_dir = _make_inventory(tmp_path, [
        _base_post("dev-020", "Test Post", wp_post_id=119, scheduled_date="2026-09-01T09:00:00"),
    ])

    mock_wp = MagicMock()
    mock_wp.update_post = AsyncMock(return_value={"wp_post_id": 119, "wp_url": "https://blog.example.com/post/"})

    inventory = InventoryManager(inventory_dir=inv_dir)

    with patch("blog_engine.tools.calendar._get_wp_handler", return_value=mock_wp), \
         patch("blog_engine.tools.calendar.InventoryManager", return_value=inventory):
        asyncio.run(reschedule_post("dev-020", "2026-10-29T09:00:00"))

    # Read back from disk
    with open(inv_dir / "dev-020.yaml", "r") as f:
        saved = yaml.safe_load(f)

    assert saved["scheduled_date"] == "2026-10-29T09:00:00"


# ---------------------------------------------------------------------------
# Test 3 — reschedule return dict contains old_date and new_date
# ---------------------------------------------------------------------------

def test_reschedule_returns_old_and_new_date(tmp_path):
    """Return dict includes post_id, wp_post_id, old_date, new_date, status."""
    inv_dir = _make_inventory(tmp_path, [
        _base_post("dev-020", "Test Post", wp_post_id=119, scheduled_date="2026-09-01T09:00:00"),
    ])

    mock_wp = MagicMock()
    mock_wp.update_post = AsyncMock(return_value={"wp_post_id": 119, "wp_url": "https://blog.example.com/post/"})

    inventory = InventoryManager(inventory_dir=inv_dir)

    with patch("blog_engine.tools.calendar._get_wp_handler", return_value=mock_wp), \
         patch("blog_engine.tools.calendar.InventoryManager", return_value=inventory):
        result = asyncio.run(reschedule_post("dev-020", "2026-10-29T09:00:00"))

    assert result["post_id"] == "dev-020"
    assert result["wp_post_id"] == 119
    assert result["old_date"] == "2026-09-01T09:00:00"
    assert result["new_date"] == "2026-10-29T09:00:00"
    assert result["status"] == "rescheduled"


# ---------------------------------------------------------------------------
# Test 4 — reschedule raises ValueError on unknown post_id
# ---------------------------------------------------------------------------

def test_reschedule_unknown_post_raises(tmp_path):
    """post_id not in inventory → ValueError before any API call."""
    inv_dir = _make_inventory(tmp_path, [])
    inventory = InventoryManager(inventory_dir=inv_dir)

    mock_wp = MagicMock()
    mock_wp.update_post = AsyncMock()

    with patch("blog_engine.tools.calendar._get_wp_handler", return_value=mock_wp), \
         patch("blog_engine.tools.calendar.InventoryManager", return_value=inventory):
        with pytest.raises(ValueError, match="not found"):
            asyncio.run(reschedule_post("dev-999", "2026-10-29T09:00:00"))

    mock_wp.update_post.assert_not_called()


# ---------------------------------------------------------------------------
# Test 5 — reschedule raises ValueError if wp_post_id missing
# ---------------------------------------------------------------------------

def test_reschedule_missing_wp_id_raises(tmp_path):
    """Inventory entry has no wp_post_id → ValueError before any API call."""
    inv_dir = _make_inventory(tmp_path, [
        _base_post("dev-020", "Test Post", wp_post_id=None, scheduled_date="2026-09-01T09:00:00"),
    ])
    inventory = InventoryManager(inventory_dir=inv_dir)

    mock_wp = MagicMock()
    mock_wp.update_post = AsyncMock()

    with patch("blog_engine.tools.calendar._get_wp_handler", return_value=mock_wp), \
         patch("blog_engine.tools.calendar.InventoryManager", return_value=inventory):
        with pytest.raises(ValueError, match="wp_post_id"):
            asyncio.run(reschedule_post("dev-020", "2026-10-29T09:00:00"))

    mock_wp.update_post.assert_not_called()


# ---------------------------------------------------------------------------
# Test 6 — get_full_calendar sorted ascending by scheduled_date
# ---------------------------------------------------------------------------

def test_get_full_calendar_sorted_by_date(tmp_path):
    """Posts returned in ascending scheduled_date order."""
    inv_dir = _make_inventory(tmp_path, [
        _base_post("dev-003", "C Post", scheduled_date="2026-12-01T09:00:00"),
        _base_post("dev-001", "A Post", scheduled_date="2026-06-15T09:00:00"),
        _base_post("dev-002", "B Post", scheduled_date="2026-09-01T09:00:00"),
    ])
    inventory = InventoryManager(inventory_dir=inv_dir)

    with patch("blog_engine.tools.calendar.InventoryManager", return_value=inventory):
        result = asyncio.run(get_full_calendar())

    dates = [r["scheduled_date"] for r in result]
    assert dates == ["2026-06-15T09:00:00", "2026-09-01T09:00:00", "2026-12-01T09:00:00"]


# ---------------------------------------------------------------------------
# Test 7 — get_full_calendar: nulls sorted last
# ---------------------------------------------------------------------------

def test_get_full_calendar_nulls_sorted_last(tmp_path):
    """Posts with no scheduled_date appear at end, not omitted."""
    inv_dir = _make_inventory(tmp_path, [
        _base_post("dev-002", "No Date Post", scheduled_date=None),
        _base_post("dev-001", "Has Date Post", scheduled_date="2026-06-15T09:00:00"),
    ])
    inventory = InventoryManager(inventory_dir=inv_dir)

    with patch("blog_engine.tools.calendar.InventoryManager", return_value=inventory):
        result = asyncio.run(get_full_calendar())

    assert len(result) == 2
    assert result[0]["post_id"] == "dev-001"
    assert result[1]["post_id"] == "dev-002"
    assert result[1]["scheduled_date"] is None


# ---------------------------------------------------------------------------
# Test 8 — get_full_calendar: status_filter excludes non-matching
# ---------------------------------------------------------------------------

def test_get_full_calendar_status_filter(tmp_path):
    """status_filter='approved' returns only approved posts."""
    inv_dir = _make_inventory(tmp_path, [
        _base_post("dev-001", "Approved Post", status="approved", scheduled_date="2026-06-15T09:00:00"),
        _base_post("dev-002", "Pending Post", status="pending", scheduled_date="2026-07-01T09:00:00"),
        _base_post("dev-003", "Published Post", status="published", scheduled_date="2026-05-01T09:00:00"),
    ])
    inventory = InventoryManager(inventory_dir=inv_dir)

    with patch("blog_engine.tools.calendar.InventoryManager", return_value=inventory):
        result = asyncio.run(get_full_calendar(status_filter="approved"))

    assert len(result) == 1
    assert result[0]["post_id"] == "dev-001"

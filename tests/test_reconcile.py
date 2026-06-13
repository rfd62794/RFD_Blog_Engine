"""
tests/test_reconcile.py

Tests for blog_engine/tools/reconcile.py
All WordPress API calls mocked — no network.
"""

import asyncio
import pytest
import yaml
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from blog_engine.tools.reconcile import (
    _normalize_title,
    reconcile_wp_post_ids,
    bulk_update_inventory,
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


def _base_inv_post(post_id, title, wp_post_id=None):
    return {
        "post_id": post_id,
        "title": title,
        "status": "published",
        "category": "",
        "notes": "",
        "tags": [],
        "wp_post_id": wp_post_id,
        "created_at": "2026-06-01T00:00:00",
    }


def _wp_post(wp_id, title, slug="some-slug"):
    return {
        "id": wp_id,
        "title": {"rendered": title},
        "date": "2026-06-21T09:00:00",
        "status": "future",
        "slug": slug,
    }


def _mock_wp_response(wp_posts):
    r = MagicMock()
    r.json.return_value = wp_posts
    wp = MagicMock()
    wp.base_url = "https://blog.example.com"
    wp.auth = ("user", "pass")
    wp._make_request = AsyncMock(return_value=r)
    return wp


# ---------------------------------------------------------------------------
# Test 1 — _normalize_title strips HTML entities
# ---------------------------------------------------------------------------

def test_normalize_strips_html_entities():
    assert _normalize_title("Zero Wasn&#8217;t Zero") == "zero wasnt zero"
    assert _normalize_title("I Almost Called It &#8220;Late Night Journey&#8221;") == "i almost called it late night journey"
    assert _normalize_title("  Extra   Spaces  ") == "extra spaces"


# ---------------------------------------------------------------------------
# Test 2 — reconcile matches by normalized title and writes wp_post_id
# ---------------------------------------------------------------------------

def test_reconcile_matches_by_normalized_title(tmp_path):
    inventory = _make_inventory(tmp_path, [
        _base_inv_post("dev-016", "Zero Wasn't Zero"),
    ])
    mock_wp = _mock_wp_response([
        _wp_post(118, "Zero Wasn&#8217;t Zero", slug="zero-wasnt-zero"),
    ])

    with patch("blog_engine.tools.reconcile._get_wp_handler", return_value=mock_wp), \
         patch("blog_engine.tools.reconcile.InventoryManager", return_value=inventory):
        result = asyncio.run(reconcile_wp_post_ids(dry_run=False))

    assert len(result["matched"]) == 1
    assert result["matched"][0]["post_id"] == "dev-016"
    assert result["matched"][0]["wp_post_id"] == 118
    assert result["dry_run"] is False

    # YAML written
    with open(inventory.inventory_dir / "dev-016.yaml") as f:
        saved = yaml.safe_load(f)
    assert saved["wp_post_id"] == 118


# ---------------------------------------------------------------------------
# Test 3 — dry_run=True returns match but writes no YAML
# ---------------------------------------------------------------------------

def test_reconcile_dry_run_no_writes(tmp_path):
    inventory = _make_inventory(tmp_path, [
        _base_inv_post("dev-016", "Zero Wasn't Zero"),
    ])
    mock_wp = _mock_wp_response([
        _wp_post(118, "Zero Wasn&#8217;t Zero", slug="zero-wasnt-zero"),
    ])
    original_mtime = (inventory.inventory_dir / "dev-016.yaml").stat().st_mtime

    with patch("blog_engine.tools.reconcile._get_wp_handler", return_value=mock_wp), \
         patch("blog_engine.tools.reconcile.InventoryManager", return_value=inventory):
        result = asyncio.run(reconcile_wp_post_ids(dry_run=True))

    assert len(result["matched"]) == 1
    assert result["dry_run"] is True
    # YAML not modified
    assert (inventory.inventory_dir / "dev-016.yaml").stat().st_mtime == original_mtime

    with open(inventory.inventory_dir / "dev-016.yaml") as f:
        saved = yaml.safe_load(f)
    assert saved.get("wp_post_id") is None


# ---------------------------------------------------------------------------
# Test 4 — reconcile skips posts that already have wp_post_id
# ---------------------------------------------------------------------------

def test_reconcile_skips_existing_wp_id(tmp_path):
    inventory = _make_inventory(tmp_path, [
        _base_inv_post("dev-020", "I Almost Called It \"Late Night Journey\"", wp_post_id=119),
    ])
    mock_wp = _mock_wp_response([
        _wp_post(119, "I Almost Called It &#8220;Late Night Journey&#8221;"),
    ])

    with patch("blog_engine.tools.reconcile._get_wp_handler", return_value=mock_wp), \
         patch("blog_engine.tools.reconcile.InventoryManager", return_value=inventory):
        result = asyncio.run(reconcile_wp_post_ids(dry_run=False))

    # Post already had wp_post_id — must not appear in matched
    assert all(m["post_id"] != "dev-020" for m in result["matched"])


# ---------------------------------------------------------------------------
# Test 5 — WP post with no inventory match appears in unmatched_wp
# ---------------------------------------------------------------------------

def test_reconcile_returns_unmatched(tmp_path):
    inventory = _make_inventory(tmp_path, [
        _base_inv_post("dev-001", "Known Post"),
    ])
    mock_wp = _mock_wp_response([
        _wp_post(92, "Known Post"),
        _wp_post(999, "Completely Unknown WP Post"),
    ])

    with patch("blog_engine.tools.reconcile._get_wp_handler", return_value=mock_wp), \
         patch("blog_engine.tools.reconcile.InventoryManager", return_value=inventory):
        result = asyncio.run(reconcile_wp_post_ids(dry_run=False))

    unmatched_wp_ids = [u["wp_post_id"] for u in result["unmatched_wp"]]
    assert 999 in unmatched_wp_ids
    assert 92 not in unmatched_wp_ids


# ---------------------------------------------------------------------------
# Test 6 — bulk_update raises and writes nothing if any post_id unknown
# ---------------------------------------------------------------------------

def test_bulk_update_validates_before_writing(tmp_path):
    inventory = _make_inventory(tmp_path, [
        _base_inv_post("dev-001", "Post One"),
        _base_inv_post("dev-002", "Post Two"),
    ])
    original_mtimes = {
        p: (inventory.inventory_dir / f"{p}.yaml").stat().st_mtime
        for p in ["dev-001", "dev-002"]
    }

    with patch("blog_engine.tools.reconcile.InventoryManager", return_value=inventory):
        with pytest.raises(ValueError, match="not found"):
            asyncio.run(bulk_update_inventory([
                {"post_id": "dev-001", "fields": {"wp_post_id": 92}},
                {"post_id": "dev-999", "fields": {"wp_post_id": 999}},  # unknown
            ]))

    # No YAML modified
    for post_id, original_mtime in original_mtimes.items():
        assert (inventory.inventory_dir / f"{post_id}.yaml").stat().st_mtime == original_mtime


# ---------------------------------------------------------------------------
# Test 7 — bulk_update applies all valid entries
# ---------------------------------------------------------------------------

def test_bulk_update_applies_all_valid(tmp_path):
    inventory = _make_inventory(tmp_path, [
        _base_inv_post("dev-001", "Post One"),
        _base_inv_post("dev-002", "Post Two"),
        _base_inv_post("dev-003", "Post Three"),
    ])

    with patch("blog_engine.tools.reconcile.InventoryManager", return_value=inventory):
        result = asyncio.run(bulk_update_inventory([
            {"post_id": "dev-001", "fields": {"wp_post_id": 92}},
            {"post_id": "dev-002", "fields": {"wp_post_id": 93, "scheduled_date": "2026-07-01T09:00:00"}},
            {"post_id": "dev-003", "fields": {"wp_post_id": 96}},
        ]))

    assert result["updated"] == 3
    assert result["failed"] == 0
    assert result["errors"] == []

    with open(inventory.inventory_dir / "dev-001.yaml") as f:
        assert yaml.safe_load(f)["wp_post_id"] == 92
    with open(inventory.inventory_dir / "dev-002.yaml") as f:
        saved = yaml.safe_load(f)
        assert saved["wp_post_id"] == 93
        assert saved["scheduled_date"] == "2026-07-01T09:00:00"
    with open(inventory.inventory_dir / "dev-003.yaml") as f:
        assert yaml.safe_load(f)["wp_post_id"] == 96

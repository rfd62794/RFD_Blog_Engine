"""
tests/test_taxonomy.py

Tests for blog_engine/tools/taxonomy.py
All WordPress API calls mocked — no network.
"""

import asyncio
import pytest
import yaml
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call

from blog_engine.tools.taxonomy import (
    list_wordpress_tags,
    list_wordpress_categories,
    get_or_create_tag,
    get_or_create_category,
    set_post_taxonomy,
)
from blog_engine.core.inventory import InventoryManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(data):
    r = MagicMock()
    r.json.return_value = data
    return r


def _mock_wp(url_responses: dict = None, default=None):
    """
    WP mock whose _make_request returns different values per URL substring.
    url_responses: {url_fragment: response_data}
    default: fallback response_data if no fragment matches.
    """
    wp = MagicMock()
    wp.base_url = "https://blog.example.com"
    wp.auth = ("user", "pass")

    async def _make_request(method, url, auth, params=None, json=None):
        if url_responses:
            for fragment, data in url_responses.items():
                if fragment in url:
                    if callable(data):
                        return _mock_response(data(method, url, params, json))
                    return _mock_response(data)
        return _mock_response(default or [])

    wp._make_request = AsyncMock(side_effect=_make_request)
    return wp


def _make_inventory(tmp_path: Path, posts: list) -> InventoryManager:
    inv_dir = tmp_path / "inventory"
    inv_dir.mkdir(parents=True, exist_ok=True)
    for post in posts:
        path = inv_dir / f"{post['post_id']}.yaml"
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(post, f, sort_keys=False, allow_unicode=True)
    return InventoryManager(inventory_dir=inv_dir)


_SAMPLE_TAGS = [
    {"id": 10, "name": "Python", "slug": "python", "count": 5},
    {"id": 11, "name": "Rust", "slug": "rust", "count": 2},
    {"id": 12, "name": "Automation", "slug": "automation", "count": 8},
]

_SAMPLE_CATEGORIES = [
    {"id": 3, "name": "Data Engineering", "slug": "data-engineering", "count": 4},
    {"id": 4, "name": "Dev Identity", "slug": "dev-identity", "count": 7},
    {"id": 27, "name": "AI &amp; Automation", "slug": "ai-automation", "count": 3},
]


# ---------------------------------------------------------------------------
# Test 1 — list_tags returns list of {id, name, slug, count}
# ---------------------------------------------------------------------------

def test_list_tags_returns_list():
    mock_wp = _mock_wp({"/tags": _SAMPLE_TAGS})

    with patch("blog_engine.tools.taxonomy._get_wp_handler", return_value=mock_wp):
        result = asyncio.run(list_wordpress_tags())

    assert len(result) == 3
    assert result[0] == {"id": 10, "name": "Python", "slug": "python", "count": 5}
    assert all("truncated" not in r for r in result)


# ---------------------------------------------------------------------------
# Test 2 — list_categories returns list of {id, name, slug, count}
# ---------------------------------------------------------------------------

def test_list_categories_returns_list():
    mock_wp = _mock_wp({"/categories": _SAMPLE_CATEGORIES})

    with patch("blog_engine.tools.taxonomy._get_wp_handler", return_value=mock_wp):
        result = asyncio.run(list_wordpress_categories())

    assert len(result) == 3
    assert result[0] == {"id": 3, "name": "Data Engineering", "slug": "data-engineering", "count": 4}
    assert all("truncated" not in r for r in result)


# ---------------------------------------------------------------------------
# Test 3 — get_or_create_tag existing: no POST, created=False
# ---------------------------------------------------------------------------

def test_get_or_create_tag_existing():
    mock_wp = _mock_wp({"/tags": _SAMPLE_TAGS})
    post_called = []

    async def _make_request(method, url, auth, params=None, json=None):
        if method == "POST":
            post_called.append(True)
        return _mock_response(_SAMPLE_TAGS)

    mock_wp._make_request = AsyncMock(side_effect=_make_request)

    with patch("blog_engine.tools.taxonomy._get_wp_handler", return_value=mock_wp):
        result = asyncio.run(get_or_create_tag("rust"))

    assert result["id"] == 11
    assert result["name"] == "Rust"
    assert result["created"] is False
    assert not post_called


# ---------------------------------------------------------------------------
# Test 4 — get_or_create_tag new: POST called, created=True
# ---------------------------------------------------------------------------

def test_get_or_create_tag_new():
    new_tag = {"id": 99, "name": "Godot", "slug": "godot", "count": 0}
    post_called = []

    async def _make_request(method, url, auth, params=None, json=None):
        if method == "POST":
            post_called.append(json)
            return _mock_response(new_tag)
        return _mock_response(_SAMPLE_TAGS)

    mock_wp = MagicMock()
    mock_wp.base_url = "https://blog.example.com"
    mock_wp.auth = ("user", "pass")
    mock_wp._make_request = AsyncMock(side_effect=_make_request)

    with patch("blog_engine.tools.taxonomy._get_wp_handler", return_value=mock_wp):
        result = asyncio.run(get_or_create_tag("Godot"))

    assert result["id"] == 99
    assert result["created"] is True
    assert len(post_called) == 1
    assert post_called[0]["name"] == "Godot"


# ---------------------------------------------------------------------------
# Test 5 — get_or_create_category existing: no POST, created=False
# ---------------------------------------------------------------------------

def test_get_or_create_category_existing():
    post_called = []

    async def _make_request(method, url, auth, params=None, json=None):
        if method == "POST":
            post_called.append(True)
        return _mock_response(_SAMPLE_CATEGORIES)

    mock_wp = MagicMock()
    mock_wp.base_url = "https://blog.example.com"
    mock_wp.auth = ("user", "pass")
    mock_wp._make_request = AsyncMock(side_effect=_make_request)

    with patch("blog_engine.tools.taxonomy._get_wp_handler", return_value=mock_wp):
        result = asyncio.run(get_or_create_category("data engineering"))

    assert result["id"] == 3
    assert result["created"] is False
    assert not post_called


def test_get_or_create_category_html_entity_match():
    """Category with &amp; in WP name matches 'AI & Automation' — no duplicate POST."""
    post_called = []

    async def _make_request(method, url, auth, params=None, json=None):
        if method == "POST":
            post_called.append(True)
        return _mock_response(_SAMPLE_CATEGORIES)

    mock_wp = MagicMock()
    mock_wp.base_url = "https://blog.example.com"
    mock_wp.auth = ("user", "pass")
    mock_wp._make_request = AsyncMock(side_effect=_make_request)

    with patch("blog_engine.tools.taxonomy._get_wp_handler", return_value=mock_wp):
        result = asyncio.run(get_or_create_category("AI & Automation"))

    assert result["id"] == 27
    assert result["created"] is False
    assert not post_called


# ---------------------------------------------------------------------------
# Test 6 — get_or_create_category new: POST called, created=True
# ---------------------------------------------------------------------------

def test_get_or_create_category_new():
    new_cat = {"id": 50, "name": "Business & Consulting", "slug": "business-consulting", "count": 0}
    post_called = []

    async def _make_request(method, url, auth, params=None, json=None):
        if method == "POST":
            post_called.append(json)
            return _mock_response(new_cat)
        return _mock_response(_SAMPLE_CATEGORIES)

    mock_wp = MagicMock()
    mock_wp.base_url = "https://blog.example.com"
    mock_wp.auth = ("user", "pass")
    mock_wp._make_request = AsyncMock(side_effect=_make_request)

    with patch("blog_engine.tools.taxonomy._get_wp_handler", return_value=mock_wp):
        result = asyncio.run(get_or_create_category("Business & Consulting"))

    assert result["id"] == 50
    assert result["created"] is True
    assert post_called[0]["name"] == "Business & Consulting"
    assert post_called[0]["parent"] == 0


# ---------------------------------------------------------------------------
# Test 7 — set_post_taxonomy resolves names to IDs, updates WP and YAML
# ---------------------------------------------------------------------------

def test_set_post_taxonomy_resolves_and_updates(tmp_path):
    inventory = _make_inventory(tmp_path, [{
        "post_id": "dev-001",
        "title": "Test Post",
        "status": "published",
        "category": "",
        "notes": "",
        "tags": [],
        "wp_post_id": 92,
        "created_at": "2026-06-01T00:00:00",
    }])

    wp_update_calls = []

    async def fake_update_post(post_id, wp_post_id, fields):
        wp_update_calls.append({"wp_post_id": wp_post_id, "fields": fields})
        return {"wp_post_id": wp_post_id, "wp_url": "https://blog.example.com/post/"}

    mock_wp = MagicMock()
    mock_wp.base_url = "https://blog.example.com"
    mock_wp.auth = ("user", "pass")
    mock_wp.update_post = fake_update_post

    # GET /tags returns existing, GET /categories returns existing
    async def _make_request(method, url, auth, params=None, json=None):
        if "/tags" in url and method == "GET":
            return _mock_response(_SAMPLE_TAGS)
        if "/categories" in url and method == "GET":
            return _mock_response(_SAMPLE_CATEGORIES)
        return _mock_response({})

    mock_wp._make_request = AsyncMock(side_effect=_make_request)

    with patch("blog_engine.tools.taxonomy._get_wp_handler", return_value=mock_wp), \
         patch("blog_engine.tools.taxonomy.InventoryManager", return_value=inventory):
        result = asyncio.run(set_post_taxonomy(
            "dev-001",
            tags=["python", "automation"],
            categories=["data engineering"],
        ))

    # WP called with integer IDs
    assert len(wp_update_calls) == 1
    assert set(wp_update_calls[0]["fields"]["tags"]) == {10, 12}
    assert 3 in wp_update_calls[0]["fields"]["categories"]

    # Inventory updated with names
    with open(inventory.inventory_dir / "dev-001.yaml") as f:
        saved = yaml.safe_load(f)
    assert "Python" in saved["tags"]
    assert "Automation" in saved["tags"]

    # Return dict correct
    assert result["post_id"] == "dev-001"
    assert result["new_tags_created"] == []
    assert result["new_categories_created"] == []


# ---------------------------------------------------------------------------
# Test 8 — set_post_taxonomy both None raises before any API call
# ---------------------------------------------------------------------------

def test_set_post_taxonomy_both_none_raises(tmp_path):
    inventory = _make_inventory(tmp_path, [{
        "post_id": "dev-001",
        "title": "Test",
        "status": "published",
        "category": "",
        "notes": "",
        "tags": [],
        "wp_post_id": 92,
        "created_at": "2026-06-01T00:00:00",
    }])

    mock_wp = MagicMock()
    mock_wp._make_request = AsyncMock()

    with patch("blog_engine.tools.taxonomy._get_wp_handler", return_value=mock_wp), \
         patch("blog_engine.tools.taxonomy.InventoryManager", return_value=inventory):
        with pytest.raises(ValueError, match="At least one of tags or categories"):
            asyncio.run(set_post_taxonomy("dev-001", tags=None, categories=None))

    mock_wp._make_request.assert_not_called()

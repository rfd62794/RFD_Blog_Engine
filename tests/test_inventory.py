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

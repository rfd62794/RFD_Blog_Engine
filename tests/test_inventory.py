"""
tests/test_inventory.py

Tests for inventory.yaml loading and parsing.
"""

import pytest
import yaml
from pathlib import Path


def test_inventory_loads(inventory):
    """Test that inventory.yaml loads correctly."""
    with open(inventory, "r") as f:
        data = yaml.safe_load(f)
    
    assert "posts" in data
    assert len(data["posts"]) == 2
    assert data["posts"][0]["post_id"] == "test-001"
    assert data["posts"][1]["post_id"] == "test-002"


def test_inventory_post_schema(inventory):
    """Test that posts have required fields."""
    with open(inventory, "r") as f:
        data = yaml.safe_load(f)
    
    post = data["posts"][0]
    
    required_fields = [
        "post_id", "title", "status", "category", "notes", "tags", "created_at"
    ]
    
    for field in required_fields:
        assert field in post, f"Missing required field: {field}"


def test_inventory_status_values(inventory):
    """Test that status field has valid values."""
    with open(inventory, "r") as f:
        data = yaml.safe_load(f)
    
    valid_statuses = ["pending", "drafted", "approved", "published"]
    
    for post in data["posts"]:
        assert post["status"] in valid_statuses, f"Invalid status: {post['status']}"


def test_inventory_tags_are_list(inventory):
    """Test that tags field is a list."""
    with open(inventory, "r") as f:
        data = yaml.safe_load(f)
    
    for post in data["posts"]:
        assert isinstance(post["tags"], list), "Tags must be a list"


def test_inventory_created_at_format(inventory):
    """Test that created_at is in ISO format."""
    from datetime import datetime
    
    with open(inventory, "r") as f:
        data = yaml.safe_load(f)
    
    for post in data["posts"]:
        # Should be parseable as ISO datetime
        datetime.fromisoformat(post["created_at"])


def test_update_status_pending_to_drafted(temp_dir):
    """Test that status updates correctly in YAML file."""
    from blog_engine.core.inventory import InventoryManager
    
    # Create temporary inventory file
    inv_path = temp_dir / "inventory.yaml"
    inv_data = {
        "posts": [
            {"post_id": "test-001", "title": "Test Post", "status": "pending", "category": "test", "notes": "", "tags": [], "created_at": "2026-06-07T00:00:00"}
        ]
    }
    with open(inv_path, "w") as f:
        yaml.safe_dump(inv_data, f)
    
    manager = InventoryManager(inv_path)
    manager.update_status("test-001", "drafted")
    
    # Verify update
    post = manager.get_post("test-001")
    assert post["status"] == "drafted"


def test_update_status_invalid_raises(temp_dir):
    """Test that ValueError is raised on invalid status string."""
    from blog_engine.core.inventory import InventoryManager
    
    inv_path = temp_dir / "inventory.yaml"
    inv_data = {
        "posts": [
            {"post_id": "test-001", "title": "Test Post", "status": "pending", "category": "test", "notes": "", "tags": [], "created_at": "2026-06-07T00:00:00"}
        ]
    }
    with open(inv_path, "w") as f:
        yaml.safe_dump(inv_data, f)
    
    manager = InventoryManager(inv_path)
    
    with pytest.raises(ValueError, match="Invalid status"):
        manager.update_status("test-001", "invalid_status")


def test_update_status_unknown_post_raises(temp_dir):
    """Test that ValueError is raised on unknown post_id."""
    from blog_engine.core.inventory import InventoryManager
    
    inv_path = temp_dir / "inventory.yaml"
    inv_data = {
        "posts": [
            {"post_id": "test-001", "title": "Test Post", "status": "pending", "category": "test", "notes": "", "tags": [], "created_at": "2026-06-07T00:00:00"}
        ]
    }
    with open(inv_path, "w") as f:
        yaml.safe_dump(inv_data, f)
    
    manager = InventoryManager(inv_path)
    
    with pytest.raises(ValueError, match="Post not found"):
        manager.update_status("unknown-001", "drafted")


def test_list_by_status_filters_correctly(temp_dir):
    """Test that list_by_status returns only posts matching status."""
    from blog_engine.core.inventory import InventoryManager
    
    inv_path = temp_dir / "inventory.yaml"
    inv_data = {
        "posts": [
            {"post_id": "test-001", "title": "Test 1", "status": "pending", "category": "test", "notes": "", "tags": [], "created_at": "2026-06-07T00:00:00"},
            {"post_id": "test-002", "title": "Test 2", "status": "drafted", "category": "test", "notes": "", "tags": [], "created_at": "2026-06-07T00:00:00"},
            {"post_id": "test-003", "title": "Test 3", "status": "pending", "category": "test", "notes": "", "tags": [], "created_at": "2026-06-07T00:00:00"}
        ]
    }
    with open(inv_path, "w") as f:
        yaml.safe_dump(inv_data, f)
    
    manager = InventoryManager(inv_path)
    pending_posts = manager.list_by_status("pending")
    
    assert len(pending_posts) == 2
    assert all(p["status"] == "pending" for p in pending_posts)
    assert set(p["post_id"] for p in pending_posts) == {"test-001", "test-003"}


def test_get_context_for_generation_returns_fields(temp_dir):
    """Test that get_context_for_generation returns all required fields."""
    from blog_engine.core.inventory import InventoryManager
    
    inv_path = temp_dir / "inventory.yaml"
    inv_data = {
        "posts": [
            {
                "post_id": "test-001",
                "title": "Test Post",
                "status": "pending",
                "category": "testing",
                "notes": "Test notes",
                "tags": ["tag1", "tag2"],
                "created_at": "2026-06-07T00:00:00"
            }
        ]
    }
    with open(inv_path, "w") as f:
        yaml.safe_dump(inv_data, f)
    
    manager = InventoryManager(inv_path)
    context = manager.get_context_for_generation("test-001")
    
    required_fields = ["post_id", "title", "category", "notes", "tags", "status"]
    for field in required_fields:
        assert field in context
    
    assert context["post_id"] == "test-001"
    assert context["title"] == "Test Post"
    assert context["category"] == "testing"
    assert context["notes"] == "Test notes"
    assert context["tags"] == ["tag1", "tag2"]
    assert context["status"] == "pending"

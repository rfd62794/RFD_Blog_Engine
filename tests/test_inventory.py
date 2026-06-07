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

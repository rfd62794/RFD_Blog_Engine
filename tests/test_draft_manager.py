"""
tests/test_draft_manager.py

Tests for DraftManager - draft CRUD, revision history, and context storage.
"""

import pytest
import json
from pathlib import Path
from blog_engine.core.draft_manager import DraftManager


def test_create_draft_success(db, temp_dir):
    """Test that create_draft creates a valid draft JSON."""
    manager = DraftManager(db, drafts_dir=temp_dir / "drafts")
    
    draft = manager.create_draft(
        post_id="test-001",
        title="Test Post",
        content="Test content"
    )
    
    assert draft["post_id"] == "test-001"
    assert draft["title"] == "Test Post"
    assert draft["status"] == "draft"
    assert draft["content"] == "Test content"
    assert draft["revision_count"] == 0
    assert draft["generation_source"] == "external"
    assert "created_at" in draft
    assert "updated_at" in draft
    
    # Check file exists
    draft_path = temp_dir / "drafts" / "test-001.json"
    assert draft_path.exists()


def test_create_draft_duplicate_raises(db, temp_dir):
    """Test that create_draft raises ValueError on duplicate post_id."""
    manager = DraftManager(db, drafts_dir=temp_dir / "drafts")
    
    manager.create_draft(
        post_id="test-001",
        title="Test Post",
        content="Test content"
    )
    
    with pytest.raises(ValueError, match="Draft already exists"):
        manager.create_draft(
            post_id="test-001",
            title="Another Title",
            content="Another content"
        )


def test_get_draft_returns_dict(db, temp_dir):
    """Test that get_draft returns parsed draft for existing post_id."""
    manager = DraftManager(db, drafts_dir=temp_dir / "drafts")
    
    manager.create_draft(
        post_id="test-001",
        title="Test Post",
        content="Test content"
    )
    
    draft = manager.get_draft("test-001")
    assert draft is not None
    assert draft["post_id"] == "test-001"
    assert draft["title"] == "Test Post"


def test_get_draft_missing_returns_none(db, temp_dir):
    """Test that get_draft returns None for unknown post_id."""
    manager = DraftManager(db, drafts_dir=temp_dir / "drafts")
    
    draft = manager.get_draft("nonexistent")
    assert draft is None


def test_update_draft_saves_revision_first(db, temp_dir):
    """Test that update_draft saves revision before updating content."""
    manager = DraftManager(db, drafts_dir=temp_dir / "drafts")
    
    manager.create_draft(
        post_id="test-001",
        title="Test Post",
        content="Original content"
    )
    
    # Update should save revision first
    manager.update_draft("test-001", "Updated content", "human")
    
    # Check revision was saved
    revisions = manager.get_revision_history("test-001")
    assert len(revisions) == 1
    assert revisions[0]["content"] == "Original content"
    assert revisions[0]["saved_by"] == "human"


def test_update_draft_increments_revision_count(db, temp_dir):
    """Test that update_draft increments revision_count."""
    manager = DraftManager(db, drafts_dir=temp_dir / "drafts")
    
    manager.create_draft(
        post_id="test-001",
        title="Test Post",
        content="Original content"
    )
    
    draft = manager.get_draft("test-001")
    assert draft["revision_count"] == 0
    
    manager.update_draft("test-001", "Updated content")
    
    draft = manager.get_draft("test-001")
    assert draft["revision_count"] == 1
    
    manager.update_draft("test-001", "Another update")
    
    draft = manager.get_draft("test-001")
    assert draft["revision_count"] == 2


def test_approve_draft_sets_status(db, temp_dir):
    """Test that approve_draft changes status to approved and sets approved_at."""
    manager = DraftManager(db, drafts_dir=temp_dir / "drafts")
    
    manager.create_draft(
        post_id="test-001",
        title="Test Post",
        content="Test content"
    )
    
    draft = manager.approve_draft("test-001", "human")
    
    assert draft["status"] == "approved"
    assert draft["approved_by"] == "human"
    assert draft["approved_at"] is not None


def test_approve_draft_already_approved_raises(db, temp_dir):
    """Test that approve_draft raises ValueError on double-approve."""
    manager = DraftManager(db, drafts_dir=temp_dir / "drafts")
    
    manager.create_draft(
        post_id="test-001",
        title="Test Post",
        content="Test content"
    )
    
    manager.approve_draft("test-001", "human")
    
    with pytest.raises(ValueError, match="Cannot approve draft with status"):
        manager.approve_draft("test-001", "human")


def test_delete_draft_removes_file(db, temp_dir):
    """Test that delete_draft removes the JSON file."""
    manager = DraftManager(db, drafts_dir=temp_dir / "drafts")
    
    manager.create_draft(
        post_id="test-001",
        title="Test Post",
        content="Test content"
    )
    
    draft_path = temp_dir / "drafts" / "test-001.json"
    assert draft_path.exists()
    
    manager.delete_draft("test-001")
    
    assert not draft_path.exists()


def test_delete_draft_clears_sqlite(db, temp_dir):
    """Test that delete_draft removes SQLite revisions and context."""
    manager = DraftManager(db, drafts_dir=temp_dir / "drafts")
    
    manager.create_draft(
        post_id="test-001",
        title="Test Post",
        content="Test content"
    )
    
    # Add some revisions and context
    manager.save_revision("test-001", "Revision 1", "human")
    manager.save_context("test-001", frame_moment="Test moment")
    
    # Verify data exists
    revisions = manager.get_revision_history("test-001")
    assert len(revisions) == 1
    context = manager.get_context("test-001")
    assert context is not None
    
    # Delete
    manager.delete_draft("test-001")
    
    # Verify SQLite cleared
    revisions = manager.get_revision_history("test-001")
    assert len(revisions) == 0
    context = manager.get_context("test-001")
    assert context is None


def test_save_revision_increments(db, temp_dir):
    """Test that save_revision increments revision_number."""
    manager = DraftManager(db, drafts_dir=temp_dir / "drafts")
    
    manager.create_draft(
        post_id="test-001",
        title="Test Post",
        content="Test content"
    )
    
    rev1 = manager.save_revision("test-001", "Content 1", "human")
    rev2 = manager.save_revision("test-001", "Content 2", "human")
    
    assert rev1 == 1
    assert rev2 == 2


def test_get_revision_history_ordered(db, temp_dir):
    """Test that get_revision_history returns revisions in ascending order."""
    manager = DraftManager(db, drafts_dir=temp_dir / "drafts")
    
    manager.create_draft(
        post_id="test-001",
        title="Test Post",
        content="Test content"
    )
    
    manager.save_revision("test-001", "Content 1", "human")
    manager.save_revision("test-001", "Content 2", "human")
    manager.save_revision("test-001", "Content 3", "human")
    
    revisions = manager.get_revision_history("test-001")
    
    assert len(revisions) == 3
    assert revisions[0]["revision_number"] == 1
    assert revisions[1]["revision_number"] == 2
    assert revisions[2]["revision_number"] == 3


def test_revert_revision_saves_current_first(db, temp_dir):
    """Test that revert_revision saves current content before reverting."""
    manager = DraftManager(db, drafts_dir=temp_dir / "drafts")
    
    manager.create_draft(
        post_id="test-001",
        title="Test Post",
        content="Original"
    )
    
    manager.update_draft("test-001", "Current content", "human")
    
    # Revert to revision 1 (original)
    manager.revert_revision("test-001", 1)
    
    # Should have 2 revisions: original (saved by update), current (saved before revert)
    revisions = manager.get_revision_history("test-001")
    assert len(revisions) == 2
    
    # The last revision should be the "current" content saved before revert
    assert revisions[-1]["content"] == "Current content"
    assert revisions[-1]["saved_by"] == "revert"


def test_revert_revision_restores_content(db, temp_dir):
    """Test that revert_revision restores content from target revision."""
    manager = DraftManager(db, drafts_dir=temp_dir / "drafts")
    
    manager.create_draft(
        post_id="test-001",
        title="Test Post",
        content="Original"
    )
    
    manager.update_draft("test-001", "Modified content", "human")
    
    # Revert to revision 1
    draft = manager.revert_revision("test-001", 1)
    
    assert draft["content"] == "Original"


def test_save_and_get_context(db, temp_dir):
    """Test that save_context and get_context work correctly."""
    manager = DraftManager(db, drafts_dir=temp_dir / "drafts")
    
    manager.save_context(
        post_id="test-001",
        raw_extraction="Raw extraction",
        frame_moment="The moment",
        frame_surprise="The surprise",
        frame_struggle="The struggle",
        frame_lesson="The lesson",
        frame_next="The next",
        related_posts=["test-002", "test-003"]
    )
    
    context = manager.get_context("test-001")
    
    assert context is not None
    assert context["post_id"] == "test-001"
    assert context["raw_extraction"] == "Raw extraction"
    assert context["frame_moment"] == "The moment"
    assert context["frame_surprise"] == "The surprise"
    assert context["frame_struggle"] == "The struggle"
    assert context["frame_lesson"] == "The lesson"
    assert context["frame_next"] == "The next"
    assert context["related_posts"] == ["test-002", "test-003"]


def test_enum_validation_tags_source(db, temp_dir):
    """Test that invalid tags_source raises ValueError."""
    manager = DraftManager(db, drafts_dir=temp_dir / "drafts")
    
    with pytest.raises(ValueError, match="Invalid tags_source"):
        manager.create_draft(
            post_id="test-001",
            title="Test",
            content="Content",
            tags_source="invalid"
        )


def test_enum_validation_generation_source(db, temp_dir):
    """Test that invalid generation_source raises ValueError."""
    manager = DraftManager(db, drafts_dir=temp_dir / "drafts")
    
    with pytest.raises(ValueError, match="Invalid generation_source"):
        manager.create_draft(
            post_id="test-001",
            title="Test",
            content="Content",
            generation_source="invalid"
        )

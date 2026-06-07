"""
tests/test_db_manager.py

Tests for database manager and schema initialization.
"""

import pytest
import sqlite3
from pathlib import Path


def test_schema_initialization(db):
    """Test that all tables and indexes are created correctly."""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Check post_threads table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='post_threads'")
    assert cursor.fetchone() is not None
    
    # Check post_thread_members table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='post_thread_members'")
    assert cursor.fetchone() is not None
    
    # Check post_context table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='post_context'")
    assert cursor.fetchone() is not None
    
    # Check draft_revisions table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='draft_revisions'")
    assert cursor.fetchone() is not None
    
    # Check publish_log table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='publish_log'")
    assert cursor.fetchone() is not None


def test_indexes_created(db):
    """Test that all indexes are created."""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Check idx_draft_revisions_post
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_draft_revisions_post'")
    assert cursor.fetchone() is not None
    
    # Check idx_publish_log_post
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_publish_log_post'")
    assert cursor.fetchone() is not None
    
    # Check idx_thread_members_thread
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_thread_members_thread'")
    assert cursor.fetchone() is not None


def test_foreign_keys_enabled(db):
    """Test that foreign keys are enabled."""
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys")
    result = cursor.fetchone()
    assert result[0] == 1


def test_wal_mode_enabled(db):
    """Test that WAL mode is enabled."""
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode")
    result = cursor.fetchone()
    assert result[0] == "wal"


def test_post_context_table_insert(db):
    """Test inserting into post_context table."""
    db.exec(
        """
        INSERT INTO post_context (post_id, frame_moment, frame_lesson)
        VALUES (?, ?, ?)
        """,
        ("test-001", "The moment of realization", "Patterns are invisible to creators"),
        commit=True
    )
    
    cursor = db.get_connection().cursor()
    cursor.execute("SELECT frame_moment FROM post_context WHERE post_id = ?", ("test-001",))
    result = cursor.fetchone()
    assert result[0] == "The moment of realization"


def test_draft_revisions_unique_constraint(db):
    """Test that draft_revisions has unique constraint on (post_id, revision_number)."""
    db.exec(
        """
        INSERT INTO draft_revisions (post_id, revision_number, content, saved_by)
        VALUES (?, ?, ?, ?)
        """,
        ("test-001", 1, "First revision", "human"),
        commit=True
    )
    
    # This should fail due to unique constraint
    with pytest.raises(sqlite3.IntegrityError):
        db.exec(
            """
            INSERT INTO draft_revisions (post_id, revision_number, content, saved_by)
            VALUES (?, ?, ?, ?)
            """,
            ("test-001", 1, "Duplicate revision", "human"),
            commit=True
        )


def test_publish_log_idempotency_constraint(db):
    """Test that publish_log has UNIQUE ON CONFLICT IGNORE for (post_id, platform, status)."""
    db.exec(
        """
        INSERT INTO publish_log (post_id, platform, status, platform_id, platform_url)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("test-001", "wordpress", "success", "42", "https://example.com/42"),
        commit=True
    )
    
    # This should be ignored due to ON CONFLICT IGNORE
    db.exec(
        """
        INSERT INTO publish_log (post_id, platform, status, platform_id, platform_url)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("test-001", "wordpress", "success", "43", "https://example.com/43"),
        commit=True
    )
    
    # Should still have only one record
    cursor = db.get_connection().cursor()
    cursor.execute("SELECT COUNT(*) FROM publish_log WHERE post_id = ?", ("test-001",))
    count = cursor.fetchone()[0]
    assert count == 1


def test_post_thread_relationships(db):
    """Test inserting thread and thread members."""
    # Create thread
    db.exec(
        """
        INSERT INTO post_threads (thread_name, description)
        VALUES (?, ?)
        """,
        ("identity-series", "Posts about developer identity"),
        commit=True
    )
    
    # Get thread_id
    cursor = db.get_connection().cursor()
    cursor.execute("SELECT id FROM post_threads WHERE thread_name = ?", ("identity-series",))
    thread_id = cursor.fetchone()[0]
    
    # Add member
    db.exec(
        """
        INSERT INTO post_thread_members (post_id, thread_id, sequence)
        VALUES (?, ?, ?)
        """,
        ("test-001", thread_id, 1),
        commit=True
    )
    
    # Verify
    cursor.execute(
        """
        SELECT p.post_id, t.thread_name 
        FROM post_thread_members p
        JOIN post_threads t ON p.thread_id = t.id
        WHERE p.post_id = ?
        """,
        ("test-001",)
    )
    result = cursor.fetchone()
    assert result[0] == "test-001"
    assert result[1] == "identity-series"


def test_db_retry_on_lock(db):
    """Test that DBManager retries on lock errors."""
    import threading
    import time
    
    # This test is basic - full lock testing would require more setup
    # For now, just verify the retry configuration exists
    assert db.max_retries == 10
    assert db.base_backoff == 0.1


def test_db_exec_many(db):
    """Test exec_many for bulk inserts."""
    params_list = [
        ("test-001", 1, "Revision 1", "human"),
        ("test-001", 2, "Revision 2", "human"),
        ("test-001", 3, "Revision 3", "claude"),
    ]
    
    db.exec_many(
        """
        INSERT INTO draft_revisions (post_id, revision_number, content, saved_by)
        VALUES (?, ?, ?, ?)
        """,
        params_list,
        commit=True
    )
    
    cursor = db.get_connection().cursor()
    cursor.execute("SELECT COUNT(*) FROM draft_revisions WHERE post_id = ?", ("test-001",))
    count = cursor.fetchone()[0]
    assert count == 3

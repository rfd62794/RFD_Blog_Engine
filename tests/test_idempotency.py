"""
tests/test_idempotency.py

Tests for idempotency behavior across both handlers.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from blog_engine.api.wordpress import WordPressHandler
from blog_engine.api.devto import DevToHandler
from blog_engine.infra.base_api_handler import BlogEngineHTTPError


@pytest.mark.asyncio
async def test_wp_idempotency_no_duplicate_log(db):
    """Two create_post calls → only one publish_log success row (ON CONFLICT IGNORE)."""
    handler = WordPressHandler(db, "https://example.com", "user", "pass")
    
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": 42,
        "link": "https://example.com/post-42"
    }
    
    with patch.object(handler, '_make_request', new_callable=AsyncMock, return_value=mock_response):
        # First call
        await handler.create_post(
            post_id="test-001",
            title="Test Post",
            content="Test content"
        )
        
        # Second call (should hit idempotency)
        await handler.create_post(
            post_id="test-001",
            title="Test Post",
            content="Test content"
        )
    
    # Check only one success row exists
    rows = db.exec(
        "SELECT COUNT(*) FROM publish_log WHERE post_id = ? AND platform = 'wordpress' AND status = 'success'",
        ("test-001",)
    ).fetchone()
    
    assert rows[0] == 1


@pytest.mark.asyncio
async def test_devto_idempotency_no_duplicate_log(db):
    """Two create_article calls → only one publish_log success row."""
    handler = DevToHandler(db, "test-api-key")
    
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": 123,
        "url": "https://dev.to/user/test-post"
    }
    
    with patch.object(handler, '_make_request', new_callable=AsyncMock, return_value=mock_response):
        # First call
        await handler.create_article(
            post_id="test-001",
            title="Test Post",
            body_markdown="Test content",
            canonical_url="https://blog.rfditservices.com/test-post"
        )
        
        # Second call (should hit idempotency)
        await handler.create_article(
            post_id="test-001",
            title="Test Post",
            body_markdown="Test content",
            canonical_url="https://blog.rfditservices.com/test-post"
        )
    
    # Check only one success row exists
    rows = db.exec(
        "SELECT COUNT(*) FROM publish_log WHERE post_id = ? AND platform = 'devto' AND status = 'success'",
        ("test-001",)
    ).fetchone()
    
    assert rows[0] == 1


@pytest.mark.asyncio
async def test_idempotency_failed_then_success(db):
    """Failed log exists → retry succeeds → success row written, failed row preserved."""
    handler = WordPressHandler(db, "https://example.com", "user", "pass")
    
    # Insert failed record
    db.exec(
        """
        INSERT INTO publish_log (post_id, platform, status, error_message)
        VALUES (?, ?, ?, ?)
        """,
        ("test-001", "wordpress", "failed", "Network error"),
        commit=True
    )
    
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": 42,
        "link": "https://example.com/post-42"
    }
    
    with patch.object(handler, '_make_request', new_callable=AsyncMock, return_value=mock_response):
        # Retry should succeed
        await handler.create_post(
            post_id="test-001",
            title="Test Post",
            content="Test content"
        )
    
    # Check both rows exist
    failed_rows = db.exec(
        "SELECT COUNT(*) FROM publish_log WHERE post_id = ? AND platform = 'wordpress' AND status = 'failed'",
        ("test-001",)
    ).fetchone()
    
    success_rows = db.exec(
        "SELECT COUNT(*) FROM publish_log WHERE post_id = ? AND platform = 'wordpress' AND status = 'success'",
        ("test-001",)
    ).fetchone()
    
    assert failed_rows[0] == 1
    assert success_rows[0] == 1

"""
tests/test_devto.py

Tests for Dev.to API handler.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from blog_engine.api.devto import DevToHandler
from blog_engine.infra.base_api_handler import BlogEngineHTTPError


def test_devto_create_article_draft(db):
    """Mock POST → 201, returns devto_id and devto_url."""
    handler = DevToHandler(db, "test-api-key")
    
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": 123,
        "url": "https://dev.to/user/test-post"
    }
    
    with patch.object(handler, '_make_request', new_callable=AsyncMock, return_value=mock_response):
        result = asyncio.run(handler.create_article(
            post_id="test-001",
            title="Test Post",
            body_markdown="Test content",
            canonical_url="https://blog.rfditservices.com/test-post"
        ))
    
    assert result["devto_id"] == 123
    assert result["devto_url"] == "https://dev.to/user/test-post"
    assert result["published"] is False


def test_devto_canonical_required(db):
    """canonical_url=None raises ValueError before HTTP call."""
    handler = DevToHandler(db, "test-api-key")
    
    with pytest.raises(ValueError, match="canonical_url is required"):
        asyncio.run(handler.create_article(
            post_id="test-001",
            title="Test Post",
            body_markdown="Test content",
            canonical_url=None
        ))


def test_devto_canonical_empty_raises(db):
    """canonical_url="" raises ValueError."""
    handler = DevToHandler(db, "test-api-key")
    
    with pytest.raises(ValueError, match="canonical_url is required"):
        asyncio.run(handler.create_article(
            post_id="test-001",
            title="Test Post",
            body_markdown="Test content",
            canonical_url=""
        ))


def test_devto_tags_truncated_at_4(db):
    """6 tags passed → only first 4 sent, warning logged."""
    handler = DevToHandler(db, "test-api-key")
    
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": 123,
        "url": "https://dev.to/user/test-post"
    }
    
    with patch.object(handler, '_make_request', new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_response
        
        result = asyncio.run(handler.create_article(
            post_id="test-001",
            title="Test Post",
            body_markdown="Test content",
            canonical_url="https://blog.rfditservices.com/test-post",
            tags=["tag1", "tag2", "tag3", "tag4", "tag5", "tag6"]
        ))
    
    # Check that only 4 tags were sent
    call_args = mock_req.call_args
    sent_tags = call_args.kwargs["json"]["article"]["tags"]
    assert len(sent_tags) == 4
    assert sent_tags == ["tag1", "tag2", "tag3", "tag4"]


def test_devto_write_publish_log_on_success(db):
    """publish_log written with status=success."""
    handler = DevToHandler(db, "test-api-key")
    
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": 123,
        "url": "https://dev.to/user/test-post"
    }
    
    with patch.object(handler, '_make_request', new_callable=AsyncMock, return_value=mock_response):
        asyncio.run(handler.create_article(
            post_id="test-001",
            title="Test Post",
            body_markdown="Test content",
            canonical_url="https://blog.rfditservices.com/test-post"
        ))
    
    row = db.exec(
        "SELECT status, platform_id, platform_url FROM publish_log WHERE post_id = ? AND platform = 'devto'",
        ("test-001",)
    ).fetchone()
    
    assert row is not None
    assert row[0] == "success"
    assert row[1] == "123"
    assert row[2] == "https://dev.to/user/test-post"


def test_devto_write_publish_log_on_failure(db):
    """publish_log written with status=failed."""
    handler = DevToHandler(db, "test-api-key")
    
    with patch.object(handler, '_make_request', new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = BlogEngineHTTPError(401, "Unauthorized")
        
        with pytest.raises(BlogEngineHTTPError):
            asyncio.run(handler.create_article(
                post_id="test-001",
                title="Test Post",
                body_markdown="Test content",
                canonical_url="https://blog.rfditservices.com/test-post"
            ))
    
    row = db.exec(
        "SELECT status, error_message FROM publish_log WHERE post_id = ? AND platform = 'devto'",
        ("test-001",)
    ).fetchone()
    
    assert row is not None
    assert row[0] == "failed"
    assert "Unauthorized" in row[1]


def test_devto_retry_on_500(db):
    """Mock 500 → 500 → 201, succeeds on third attempt."""
    handler = DevToHandler(db, "test-api-key")
    
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": 123,
        "url": "https://dev.to/user/test-post"
    }
    
    with patch.object(handler, '_make_request', new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = [
            BlogEngineHTTPError(500, "Server Error"),
            BlogEngineHTTPError(500, "Server Error"),
            mock_response
        ]
        
        result = asyncio.run(handler.create_article(
            post_id="test-001",
            title="Test Post",
            body_markdown="Test content",
            canonical_url="https://blog.rfditservices.com/test-post"
        ))
    
    assert result["devto_id"] == 123
    assert mock_req.call_count == 3


def test_devto_no_retry_on_401(db):
    """Mock 401, fails immediately."""
    handler = DevToHandler(db, "test-api-key")
    
    with patch.object(handler, '_make_request', new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = BlogEngineHTTPError(401, "Unauthorized")
        
        with pytest.raises(BlogEngineHTTPError):
            asyncio.run(handler.create_article(
                post_id="test-001",
                title="Test Post",
                body_markdown="Test content",
                canonical_url="https://blog.rfditservices.com/test-post"
            ))
    
    assert mock_req.call_count == 1


def test_devto_idempotency_returns_existing(db):
    """Existing success in publish_log → returns existing, no HTTP call."""
    handler = DevToHandler(db, "test-api-key")
    
    db.exec(
        """
        INSERT INTO publish_log (post_id, platform, status, platform_id, platform_url)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("test-001", "devto", "success", "123", "https://dev.to/user/test-post"),
        commit=True
    )
    
    with patch.object(handler, '_make_request', new_callable=AsyncMock) as mock_req:
        result = asyncio.run(handler.create_article(
            post_id="test-001",
            title="Test Post",
            body_markdown="Test content",
            canonical_url="https://blog.rfditservices.com/test-post"
        ))
    
    assert mock_req.call_count == 0
    assert result["devto_id"] == 123
    assert result["devto_url"] == "https://dev.to/user/test-post"


def test_devto_update_article(db):
    """Mock PUT → 200, returns updated devto_url."""
    handler = DevToHandler(db, "test-api-key")
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": 123,
        "url": "https://dev.to/user/test-post-updated"
    }
    
    with patch.object(handler, '_make_request', new_callable=AsyncMock, return_value=mock_response):
        result = asyncio.run(handler.update_article(
            post_id="test-001",
            devto_id=123,
            fields={"title": "Updated Title"}
        ))
    
    assert result["devto_id"] == 123
    assert result["devto_url"] == "https://dev.to/user/test-post-updated"

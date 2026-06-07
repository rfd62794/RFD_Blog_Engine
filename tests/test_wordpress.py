"""
tests/test_wordpress.py

Tests for WordPress API handler.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from blog_engine.api.wordpress import WordPressHandler
from blog_engine.infra.base_api_handler import BlogEngineHTTPError


def test_wp_create_post_draft(db):
    """Mock POST → 201, returns wp_post_id and wp_url, status=draft."""
    handler = WordPressHandler(db, "https://example.com", "user", "pass")
    
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": 42,
        "link": "https://example.com/post-42"
    }
    
    with patch.object(handler, '_make_request', new_callable=AsyncMock, return_value=mock_response):
        result = asyncio.run(handler.create_post(
            post_id="test-001",
            title="Test Post",
            content="Test content",
            status="draft"
        ))
    
    assert result["wp_post_id"] == 42
    assert result["wp_url"] == "https://example.com/post-42"
    assert result["status"] == "draft"


def test_wp_create_post_publish(db):
    """Mock POST with status=publish → returns published status."""
    handler = WordPressHandler(db, "https://example.com", "user", "pass")
    
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": 42,
        "link": "https://example.com/post-42"
    }
    
    with patch.object(handler, '_make_request', new_callable=AsyncMock, return_value=mock_response):
        result = asyncio.run(handler.create_post(
            post_id="test-001",
            title="Test Post",
            content="Test content",
            status="publish"
        ))
    
    assert result["status"] == "publish"


def test_wp_invalid_status_raises(db):
    """status="live" raises ValueError."""
    handler = WordPressHandler(db, "https://example.com", "user", "pass")
    
    with pytest.raises(ValueError, match="Invalid status"):
        asyncio.run(handler.create_post(
            post_id="test-001",
            title="Test Post",
            content="Test content",
            status="live"
        ))


def test_wp_write_publish_log_on_success(db):
    """publish_log row written with status=success after create."""
    handler = WordPressHandler(db, "https://example.com", "user", "pass")
    
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": 42,
        "link": "https://example.com/post-42"
    }
    
    with patch.object(handler, '_make_request', new_callable=AsyncMock, return_value=mock_response):
        asyncio.run(handler.create_post(
            post_id="test-001",
            title="Test Post",
            content="Test content"
        ))
    
    # Check publish_log
    row = db.exec(
        "SELECT status, platform_id, platform_url FROM publish_log WHERE post_id = ? AND platform = 'wordpress'",
        ("test-001",)
    ).fetchone()
    
    assert row is not None
    assert row[0] == "success"
    assert row[1] == "42"
    assert row[2] == "https://example.com/post-42"


def test_wp_write_publish_log_on_failure(db):
    """publish_log row written with status=failed after 4xx."""
    handler = WordPressHandler(db, "https://example.com", "user", "pass")
    
    with patch.object(handler, '_make_request', new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = BlogEngineHTTPError(401, "Unauthorized")
        
        with pytest.raises(BlogEngineHTTPError):
            asyncio.run(handler.create_post(
                post_id="test-001",
                title="Test Post",
                content="Test content"
            ))
    
    # Check publish_log
    row = db.exec(
        "SELECT status, error_message FROM publish_log WHERE post_id = ? AND platform = 'wordpress'",
        ("test-001",)
    ).fetchone()
    
    assert row is not None
    assert row[0] == "failed"
    assert "Unauthorized" in row[1]


def test_wp_retry_on_500(db):
    """Mock 500 → 500 → 201, succeeds on third attempt."""
    handler = WordPressHandler(db, "https://example.com", "user", "pass")
    
    mock_response_500 = MagicMock()
    mock_response_500.status_code = 500
    
    mock_response_201 = MagicMock()
    mock_response_201.status_code = 201
    mock_response_201.json.return_value = {
        "id": 42,
        "link": "https://example.com/post-42"
    }
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.request.side_effect = [
            mock_response_500,
            mock_response_500,
            mock_response_201
        ]
        
        result = asyncio.run(handler.create_post(
            post_id="test-001",
            title="Test Post",
            content="Test content"
        ))
    
    assert result["wp_post_id"] == 42
    assert mock_client.return_value.__aenter__.return_value.request.call_count == 3


def test_wp_no_retry_on_401(db):
    """Mock 401, fails immediately, no retries."""
    handler = WordPressHandler(db, "https://example.com", "user", "pass")
    
    with patch.object(handler, '_make_request', new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = BlogEngineHTTPError(401, "Unauthorized")
        
        with pytest.raises(BlogEngineHTTPError):
            asyncio.run(handler.create_post(
                post_id="test-001",
                title="Test Post",
                content="Test content"
            ))
    
    assert mock_req.call_count == 1


def test_wp_idempotency_returns_existing(db):
    """publish_log has success row → returns existing URL, no HTTP call."""
    handler = WordPressHandler(db, "https://example.com", "user", "pass")
    
    # Insert existing success record
    db.exec(
        """
        INSERT INTO publish_log (post_id, platform, status, platform_id, platform_url)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("test-001", "wordpress", "success", "42", "https://example.com/post-42"),
        commit=True
    )
    
    with patch.object(handler, '_make_request', new_callable=AsyncMock) as mock_req:
        result = asyncio.run(handler.create_post(
            post_id="test-001",
            title="Test Post",
            content="Test content"
        ))
    
    # Should not have called the API
    assert mock_req.call_count == 0
    assert result["wp_post_id"] == 42
    assert result["wp_url"] == "https://example.com/post-42"


def test_wp_update_post(db):
    """Mock PATCH → 200, returns updated wp_url."""
    handler = WordPressHandler(db, "https://example.com", "user", "pass")
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": 42,
        "link": "https://example.com/post-42-updated"
    }
    
    with patch.object(handler, '_make_request', new_callable=AsyncMock, return_value=mock_response):
        result = asyncio.run(handler.update_post(
            post_id="test-001",
            wp_post_id=42,
            fields={"title": "Updated Title"}
        ))
    
    assert result["wp_post_id"] == 42
    assert result["wp_url"] == "https://example.com/post-42-updated"


def test_wp_get_post(db):
    """Mock GET → 200, returns raw response dict."""
    handler = WordPressHandler(db, "https://example.com", "user", "pass")
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": 42,
        "title": {"rendered": "Test Post"},
        "content": {"rendered": "Test content"}
    }
    
    with patch.object(handler, '_make_request', new_callable=AsyncMock, return_value=mock_response):
        result = asyncio.run(handler.get_post(42))
    
    assert result["id"] == 42
    assert result["title"]["rendered"] == "Test Post"


def test_make_request_retry_on_500(db):
    """Test _make_request directly: retry on 500."""
    handler = WordPressHandler(db, "https://example.com", "user", "pass")
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.request.side_effect = [
            MagicMock(status_code=500),
            MagicMock(status_code=500),
            mock_response
        ]
        
        result = asyncio.run(handler._make_request("GET", "https://example.com"))
    
    assert result.status_code == 200


def test_make_request_no_retry_on_401(db):
    """Test _make_request directly: no retry on 401."""
    handler = WordPressHandler(db, "https://example.com", "user", "pass")
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.request.return_value = MagicMock(status_code=401)
        
        with pytest.raises(BlogEngineHTTPError) as exc:
            asyncio.run(handler._make_request("GET", "https://example.com"))
    
    assert exc.value.status_code == 401

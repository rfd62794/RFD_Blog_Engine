"""
tests/test_wordpress_media.py

Tests for WordPress media upload and featured_media on create_post.
All HTTP is mocked — no network.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from blog_engine.api.wordpress import WordPressHandler


def test_upload_media_posts_multipart_and_sets_alt_text(db, tmp_path):
    """upload_media POSTs a multipart `file` field, then sets alt_text via _make_request."""
    handler = WordPressHandler(db, "https://example.com", "user", "pass")

    image_path = tmp_path / "card.png"
    image_path.write_bytes(b"\x89PNG fake bytes")

    upload_response = MagicMock()
    upload_response.json.return_value = {"id": 77}

    with patch("httpx.AsyncClient") as mock_client:
        mock_post = AsyncMock(return_value=upload_response)
        mock_client.return_value.__aenter__.return_value.post = mock_post

        with patch.object(handler, "_make_request", new_callable=AsyncMock) as mock_req:
            media_id = asyncio.run(handler.upload_media(str(image_path), "alt text"))

    assert media_id == 77

    # Upload call: multipart with a `file` field carrying (name, bytes, mime)
    post_call = mock_post.call_args
    assert post_call.args[0] == "https://example.com/wp-json/wp/v2/media"
    assert post_call.kwargs["auth"] == ("user", "pass")
    filename, data, mime = post_call.kwargs["files"]["file"]
    assert filename == "card.png"
    assert data == b"\x89PNG fake bytes"
    assert mime == "image/png"

    # Alt text call: ordinary JSON POST through _make_request
    mock_req.assert_called_once()
    assert mock_req.call_args.args[0] == "POST"
    assert mock_req.call_args.args[1] == "https://example.com/wp-json/wp/v2/media/77"
    assert mock_req.call_args.kwargs["json"] == {"alt_text": "alt text"}


def test_create_post_includes_featured_media(db):
    """create_post(..., featured_media=123) puts featured_media in the JSON payload."""
    handler = WordPressHandler(db, "https://example.com", "user", "pass")

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": 42,
        "link": "https://example.com/post-42"
    }

    with patch.object(handler, '_make_request', new_callable=AsyncMock, return_value=mock_response) as mock_req:
        asyncio.run(handler.create_post(
            post_id="test-001",
            title="Test Post",
            content="Test content",
            featured_media=123
        ))

    assert mock_req.call_args.kwargs["json"]["featured_media"] == 123


def test_create_post_omits_featured_media_when_none(db):
    """Without featured_media, the payload carries no featured_media key."""
    handler = WordPressHandler(db, "https://example.com", "user", "pass")

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": 42,
        "link": "https://example.com/post-42"
    }

    with patch.object(handler, '_make_request', new_callable=AsyncMock, return_value=mock_response) as mock_req:
        asyncio.run(handler.create_post(
            post_id="test-001",
            title="Test Post",
            content="Test content"
        ))

    assert "featured_media" not in mock_req.call_args.kwargs["json"]

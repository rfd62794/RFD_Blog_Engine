"""
tests/test_validate_metadata.py

Tests for metadata validator tool.
All external API calls are mocked.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from blog_engine.tools.validate_metadata import (
    validate_post_metadata,
    audit_all_posts,
    check_schedule_collisions,
    get_permalink_structure,
    fix_devto_canonical,
)


# ───────────────────────────────────────────────────────────────
# Test Anchors (§3)
# ───────────────────────────────────────────────────────────────


def test_validator_flags_missing_excerpt(db):
    """Anchor 1: Validator flags missing or empty excerpt."""
    with patch("blog_engine.tools.validate_metadata._get_post_from_db") as mock_get_db, \
         patch("blog_engine.tools.validate_metadata._wp_api_get", new_callable=AsyncMock) as mock_wp:
        
        mock_get_db.return_value = {
            "post_id": "dev-001",
            "platforms": {"wordpress": {"id": "123", "url": "https://blog.rfditservices.com/test"}}
        }
        
        # WP returns empty excerpt
        mock_wp.return_value = {
            "id": 123,
            "excerpt": {"rendered": ""},
            "categories": [1],
            "tags": [1, 2, 3],
            "featured_media": 456,
            "link": "https://blog.rfditservices.com/test/",
            "slug": "test",
            "status": "publish",
        }
        
        result = asyncio.run(validate_post_metadata("dev-001"))
        
        assert result["excerpt_present"] is False
        assert result["excerpt_non_empty"] is False


def test_validator_flags_empty_categories(db):
    """Anchor 2: Validator flags empty categories."""
    with patch("blog_engine.tools.validate_metadata._get_post_from_db") as mock_get_db, \
         patch("blog_engine.tools.validate_metadata._wp_api_get", new_callable=AsyncMock) as mock_wp:
        
        mock_get_db.return_value = {
            "post_id": "dev-002",
            "platforms": {"wordpress": {"id": "124", "url": "https://blog.rfditservices.com/test2"}}
        }
        
        mock_wp.return_value = {
            "id": 124,
            "excerpt": {"rendered": "Valid excerpt"},
            "categories": [],  # Empty categories
            "tags": [1, 2, 3],
            "featured_media": 456,
            "link": "https://blog.rfditservices.com/test2/",
            "slug": "test2",
            "status": "publish",
        }
        
        result = asyncio.run(validate_post_metadata("dev-002"))
        
        assert result["has_categories"] is False


def test_validator_flags_missing_featured_image(db):
    """Anchor 3: Validator flags missing featured image."""
    with patch("blog_engine.tools.validate_metadata._get_post_from_db") as mock_get_db, \
         patch("blog_engine.tools.validate_metadata._wp_api_get", new_callable=AsyncMock) as mock_wp:
        
        mock_get_db.return_value = {
            "post_id": "dev-003",
            "platforms": {"wordpress": {"id": "125", "url": "https://blog.rfditservices.com/test3"}}
        }
        
        mock_wp.return_value = {
            "id": 125,
            "excerpt": {"rendered": "Valid excerpt"},
            "categories": [1],
            "tags": [1, 2, 3],
            "featured_media": 0,  # No featured image
            "link": "https://blog.rfditservices.com/test3/",
            "slug": "test3",
            "status": "publish",
        }
        
        result = asyncio.run(validate_post_metadata("dev-003"))
        
        assert result["has_featured_image"] is False


def test_validator_passes_complete_post(db):
    """Anchor 4: Validator passes complete, valid post."""
    with patch("blog_engine.tools.validate_metadata._get_post_from_db") as mock_get_db, \
         patch("blog_engine.tools.validate_metadata._wp_api_get", new_callable=AsyncMock) as mock_wp:
        
        mock_get_db.return_value = {
            "post_id": "dev-004",
            "platforms": {"wordpress": {"id": "126", "url": "https://blog.rfditservices.com/test4"}}
        }
        
        mock_wp.return_value = {
            "id": 126,
            "excerpt": {"rendered": "A valid excerpt here"},
            "categories": [1, 2],  # Multiple categories
            "tags": [1, 2, 3, 4],  # 4 tags >= 3
            "featured_media": 789,
            "link": "https://blog.rfditservices.com/test4/",
            "slug": "test4",
            "status": "publish",
        }
        
        result = asyncio.run(validate_post_metadata("dev-004"))
        
        assert result["excerpt_present"] is True
        assert result["excerpt_non_empty"] is True
        assert result["has_categories"] is True
        assert result["has_minimum_tags"] is True
        assert result["has_featured_image"] is True
        assert result["slug_not_query_fallback"] is True
        assert result["schedule_valid"] is True


def test_validator_flags_canonical_mismatch(db):
    """Anchor 5: Validator flags Dev.to canonical URL mismatch."""
    with patch("blog_engine.tools.validate_metadata._get_post_from_db") as mock_get_db, \
         patch("blog_engine.tools.validate_metadata._wp_api_get", new_callable=AsyncMock) as mock_wp, \
         patch("blog_engine.tools.validate_metadata._devto_api_get", new_callable=AsyncMock) as mock_devto:
        
        mock_get_db.return_value = {
            "post_id": "dev-005",
            "platforms": {
                "wordpress": {"id": "127", "url": "https://blog.rfditservices.com/test5"},
                "devto": {"id": "98765", "url": "https://dev.to/rfd/test5"}
            }
        }
        
        mock_wp.return_value = {
            "id": 127,
            "excerpt": {"rendered": "Valid excerpt"},
            "categories": [1],
            "tags": [1, 2, 3],
            "featured_media": 789,
            "link": "https://blog.rfditservices.com/test5/",
            "slug": "test5",
            "status": "publish",
        }
        
        # Dev.to has wrong canonical URL (pointing to /test/ instead of /test5/)
        mock_devto.return_value = {
            "id": 98765,
            "canonical_url": "https://blog.rfditservices.com/test/",
            "url": "https://dev.to/rfd/test5",
        }
        
        result = asyncio.run(validate_post_metadata("dev-005"))
        
        assert result["canonical_matches"] is False
        assert any("Canonical mismatch" in err for err in result["errors"])


def test_validator_flags_schedule_collision(db):
    """Anchor 6: Validator detects schedule collisions (via check_schedule_collisions)."""
    posts_data = [
        {"post_id": "dev-006", "scheduled_date": "2026-07-01T09:00:00"},
        {"post_id": "dev-007", "scheduled_date": "2026-07-01T09:00:00"},  # Same date
        {"post_id": "dev-008", "scheduled_date": "2026-07-02T09:00:00"},  # Different
    ]
    
    collisions = check_schedule_collisions(posts_data)
    
    assert len(collisions) == 1
    assert collisions[0][0] == "dev-006"
    assert collisions[0][1] == "dev-007"
    assert collisions[0][2] == "2026-07-01T09:00:00"


def test_canonical_fix_builds_correct_payload(db):
    """Anchor 7: Canonical fix builds correct API payload."""
    with patch("aiohttp.ClientSession") as mock_session_class:
        # Setup mock session
        mock_session = MagicMock()
        mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_class.return_value.__aexit__ = AsyncMock(return_value=False)
        
        # Mock GET response (reading current article)
        mock_get_response = AsyncMock()
        mock_get_response.status = 200
        mock_get_response.json = AsyncMock(return_value={
            "id": 3844728,
            "canonical_url": "https://wrong-url.com/old-post",
            "title": "Test Post",
        })
        
        # Mock PUT response (updating article)
        mock_put_response = AsyncMock()
        mock_put_response.status = 200
        mock_put_response.json = AsyncMock(return_value={
            "id": 3844728,
            "canonical_url": "https://blog.rfditservices.com/correct-post/",
            "title": "Test Post",
        })
        
        # Setup mock session methods
        mock_session.get = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_get_response),
            __aexit__=AsyncMock(return_value=False)
        ))
        mock_session.put = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_put_response),
            __aexit__=AsyncMock(return_value=False)
        ))
        
        result = asyncio.run(fix_devto_canonical(
            "3844728",
            "https://blog.rfditservices.com/correct-post/"
        ))
        
        assert result["article_id"] == "3844728"
        assert result["before"] == "https://wrong-url.com/old-post"
        assert result["after"] == "https://blog.rfditservices.com/correct-post/"
        assert result["success"] is True

"""
tests/test_devto_sync.py

Tests for blog_engine/devto_sync.py
All external HTTP calls mocked — no live WP or Dev.to writes.
"""

import asyncio
import json
import pytest
import tempfile
import shutil
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from blog_engine.devto_sync import (
    _build_action_plan,
    _has_devto_record,
    _get_start_date,
    _ensure_sync_log_table,
    run_sync,
    devto_sync_dry_run,
    DEVTO_SYNC_START_DATE_ENV,
    DEFAULT_START_DATE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_wp_post(
    wp_id: int,
    title: str = "Test Post",
    link: str = "https://blog.example.com/2026/06/11/test-post/",
    status: str = "publish",
    pub_date: str = "2026-06-11T09:00:00",
    excerpt: str = "A real excerpt.",
    tags: list = None,
):
    return {
        "id": wp_id,
        "title": {"rendered": title},
        "link": link,
        "status": status,
        "date": pub_date,
        "excerpt": {"rendered": excerpt},
        "content": {"rendered": "<p>Content</p>"},
        "tags": tags or [],
        "categories": [1],
        "featured_media": 0,
        "slug": "test-post",
    }


def _seed_wp_publish_log(db, wp_id: int, engine_post_id: str):
    """Write a wordpress success record so _has_devto_record can resolve it."""
    db.exec(
        """
        INSERT OR IGNORE INTO publish_log (post_id, platform, status, platform_id, platform_url, error_message)
        VALUES (?, 'wordpress', 'success', ?, 'https://blog.example.com/post', NULL)
        """,
        (engine_post_id, str(wp_id)),
        commit=True,
    )


def _seed_devto_publish_log(db, engine_post_id: str):
    db.exec(
        """
        INSERT OR IGNORE INTO publish_log (post_id, platform, status, platform_id, platform_url, error_message)
        VALUES (?, 'devto', 'success', '99999', 'https://dev.to/user/test', NULL)
        """,
        (engine_post_id,),
        commit=True,
    )


# ---------------------------------------------------------------------------
# Test 1 — skip post with existing devto_id
# ---------------------------------------------------------------------------

def test_sync_skips_post_with_existing_devto_id(db):
    """Post already syndicated → action=skip_existing, not included in would_syndicate."""
    _ensure_sync_log_table(db)
    _seed_wp_publish_log(db, 42, "dev-001")
    _seed_devto_publish_log(db, "dev-001")

    post = _make_wp_post(42, pub_date="2026-06-11T09:00:00")
    start = date(2026, 6, 11)

    with patch("blog_engine.devto_sync._verify_canonical", new_callable=AsyncMock, return_value=True):
        plan = asyncio.run(_build_action_plan([post], db, start))

    assert len(plan) == 1
    assert plan[0]["action"] == "skip_existing"


# ---------------------------------------------------------------------------
# Test 2 — skip post before start date
# ---------------------------------------------------------------------------

def test_sync_skips_post_before_start_date(db):
    """Post published before DEVTO_SYNC_START_DATE → action=skip_window."""
    _ensure_sync_log_table(db)

    post = _make_wp_post(10, pub_date="2026-01-01T09:00:00")
    start = date(2026, 6, 11)

    with patch("blog_engine.devto_sync._verify_canonical", new_callable=AsyncMock, return_value=True):
        plan = asyncio.run(_build_action_plan([post], db, start))

    assert plan[0]["action"] == "skip_window"


# ---------------------------------------------------------------------------
# Test 3 — refuse unresolvable canonical (non-200)
# ---------------------------------------------------------------------------

def test_sync_refuses_unresolvable_canonical(db):
    """Canonical URL returns non-200 → action=refuse_canonical, no article created."""
    _ensure_sync_log_table(db)

    post = _make_wp_post(20, pub_date="2026-06-12T09:00:00")
    start = date(2026, 6, 11)

    with patch("blog_engine.devto_sync._verify_canonical", new_callable=AsyncMock, return_value=False):
        plan = asyncio.run(_build_action_plan([post], db, start))

    assert plan[0]["action"] == "refuse_canonical"
    assert "200" in plan[0]["reason"]


# ---------------------------------------------------------------------------
# Test 4 — uses live WP link field, not guid
# ---------------------------------------------------------------------------

def test_sync_uses_live_link_not_guid(db):
    """Canonical submitted to Dev.to is the WP `link` field, never the ?p= guid."""
    _ensure_sync_log_table(db)
    _seed_wp_publish_log(db, 30, "dev-002")

    pretty_link = "https://blog.example.com/2026/06/11/some-post/"
    post = _make_wp_post(30, link=pretty_link, pub_date="2026-06-11T09:00:00")
    start = date(2026, 6, 11)

    with patch("blog_engine.devto_sync._verify_canonical", new_callable=AsyncMock, return_value=True):
        plan = asyncio.run(_build_action_plan([post], db, start))

    assert plan[0]["action"] == "would_syndicate"
    # Confirm the link stored in plan is the pretty permalink
    assert plan[0]["link"] == pretty_link
    assert "?p=" not in plan[0]["link"]


# ---------------------------------------------------------------------------
# Test 5 — refuse on validation failure (query-string slug)
# ---------------------------------------------------------------------------

def test_sync_refuses_on_validation_failure(db):
    """Post with ?p= slug → refuse_validation before canonical check."""
    _ensure_sync_log_table(db)

    post = _make_wp_post(
        40,
        link="https://blog.example.com/?p=40",
        pub_date="2026-06-11T09:00:00",
    )
    start = date(2026, 6, 11)

    # _verify_canonical should never be called because validation fails first
    with patch("blog_engine.devto_sync._verify_canonical", new_callable=AsyncMock, return_value=True) as mock_verify:
        plan = asyncio.run(_build_action_plan([post], db, start))
        mock_verify.assert_not_called()

    assert plan[0]["action"] == "refuse_validation"
    assert "?p=" in plan[0]["reason"]


# ---------------------------------------------------------------------------
# Test 6 — creates article with correct canonical payload
# ---------------------------------------------------------------------------

def test_sync_creates_article_with_correct_canonical_payload(db):
    """run_sync creates Dev.to article with canonical_url = WP link field."""
    _ensure_sync_log_table(db)
    _seed_wp_publish_log(db, 50, "dev-003")

    pretty_link = "https://blog.example.com/2026/06/11/correct-canonical/"
    post = _make_wp_post(50, link=pretty_link, pub_date="2026-06-11T09:00:00")

    mock_wp = MagicMock()
    mock_wp.get_posts = AsyncMock(return_value=[post])
    mock_wp.get_post = AsyncMock(return_value=post)

    captured_canonical = {}

    async def fake_create_article(post_id, title, body_markdown, canonical_url, tags, published):
        captured_canonical["url"] = canonical_url
        return {"devto_id": 99999, "devto_url": "https://dev.to/user/correct-canonical", "published": True}

    mock_devto = MagicMock()
    mock_devto.create_article = fake_create_article

    with patch("blog_engine.devto_sync._get_wp_handler", return_value=mock_wp), \
         patch("blog_engine.devto_sync._get_devto_handler", return_value=mock_devto), \
         patch("blog_engine.devto_sync._get_db", return_value=db), \
         patch("blog_engine.devto_sync._verify_canonical", new_callable=AsyncMock, return_value=True), \
         patch("blog_engine.devto_sync._get_start_date", return_value=date(2026, 6, 11)), \
         patch.dict("os.environ", {"DEVTO_API_KEY": "test-key"}):
        result = asyncio.run(run_sync(dry_run=False))

    assert captured_canonical["url"] == pretty_link
    assert result["created"] == 1


# ---------------------------------------------------------------------------
# Test 7 — dry run writes nothing
# ---------------------------------------------------------------------------

def test_dry_run_writes_nothing(db):
    """--dry-run returns plan and counts but makes no DB writes and no HTTP calls."""
    _ensure_sync_log_table(db)
    _seed_wp_publish_log(db, 60, "dev-004")

    post = _make_wp_post(60, pub_date="2026-06-12T09:00:00")

    mock_wp = MagicMock()
    mock_wp.get_posts = AsyncMock(return_value=[post])
    mock_wp.get_post = AsyncMock(return_value=post)

    mock_devto = MagicMock()
    mock_devto.create_article = AsyncMock()

    with patch("blog_engine.devto_sync._get_wp_handler", return_value=mock_wp), \
         patch("blog_engine.devto_sync._get_devto_handler", return_value=mock_devto), \
         patch("blog_engine.devto_sync._get_db", return_value=db), \
         patch("blog_engine.devto_sync._verify_canonical", new_callable=AsyncMock, return_value=True), \
         patch("blog_engine.devto_sync._get_start_date", return_value=date(2026, 6, 11)), \
         patch.dict("os.environ", {"DEVTO_API_KEY": "test-key"}):
        result = asyncio.run(run_sync(dry_run=True))

    # No article should have been created via API
    mock_devto.create_article.assert_not_called()

    # No devto_sync_log rows written
    rows = db.exec("SELECT COUNT(*) FROM devto_sync_log").fetchone()
    assert rows[0] == 0

    assert result["dry_run"] is True
    assert result["created"] == 1  # counted in plan, not written


# ---------------------------------------------------------------------------
# Test 8 — records action to publish_log equivalent (devto_sync_log)
# ---------------------------------------------------------------------------

def test_sync_records_action_to_publish_log(db):
    """Successful sync writes a devto_sync_log row with action=created."""
    _ensure_sync_log_table(db)
    _seed_wp_publish_log(db, 70, "dev-005")

    post = _make_wp_post(70, pub_date="2026-06-12T09:00:00")

    mock_wp = MagicMock()
    mock_wp.get_posts = AsyncMock(return_value=[post])
    mock_wp.get_post = AsyncMock(return_value=post)

    mock_devto = MagicMock()
    mock_devto.create_article = AsyncMock(
        return_value={"devto_id": 88888, "devto_url": "https://dev.to/user/post", "published": True}
    )

    with patch("blog_engine.devto_sync._get_wp_handler", return_value=mock_wp), \
         patch("blog_engine.devto_sync._get_devto_handler", return_value=mock_devto), \
         patch("blog_engine.devto_sync._get_db", return_value=db), \
         patch("blog_engine.devto_sync._verify_canonical", new_callable=AsyncMock, return_value=True), \
         patch("blog_engine.devto_sync._get_start_date", return_value=date(2026, 6, 11)), \
         patch.dict("os.environ", {"DEVTO_API_KEY": "test-key"}):
        result = asyncio.run(run_sync(dry_run=False))

    row = db.exec(
        "SELECT action, devto_id FROM devto_sync_log WHERE wp_post_id=70"
    ).fetchone()
    assert row is not None
    assert row[0] == "created"
    assert row[1] == "88888"


# ---------------------------------------------------------------------------
# Test 9 — update_wordpress_post accepts date (rider)
# ---------------------------------------------------------------------------

def test_update_wordpress_post_accepts_date(db):
    """update_wordpress_post passes date field to WP update_post."""
    from blog_engine.api.wordpress import WordPressHandler

    handler = WordPressHandler(db, "https://example.com", "user", "pass")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": 115,
        "link": "https://example.com/2026/08/09/some-post/"
    }

    captured_fields = {}

    async def fake_make_request(method, url, auth=None, json=None, params=None, **kwargs):
        captured_fields.update(json or {})
        return mock_response

    with patch.object(handler, "_make_request", side_effect=fake_make_request):
        result = asyncio.run(
            handler.update_post(
                post_id="dev-008",
                wp_post_id=115,
                fields={"date": "2026-08-09T09:00:00", "status": "future"},
            )
        )

    assert captured_fields.get("date") == "2026-08-09T09:00:00"
    assert result["wp_post_id"] == 115

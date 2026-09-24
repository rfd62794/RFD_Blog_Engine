"""
tests/test_backfill.py

Tests for blog_engine/core/backfill.py — the mapping walker that backfills
lane/category/tags/featured-image/excerpt onto existing WordPress posts.
All WordPress calls and the featured-image render are mocked — no network.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import yaml

from blog_engine.core.backfill import walk
from blog_engine.infra.base_api_handler import BlogEngineHTTPError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_mapping(tmp_path: Path, rows: list) -> str:
    path = tmp_path / "backfill_mapping.yaml"
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump({"posts": rows}, f, sort_keys=False)
    return str(path)


def _fake_post(wp_id: int, excerpt: str = "<p>Existing excerpt.</p>",
               content: str = "<p>body</p>") -> dict:
    return {
        "id": wp_id,
        "title": {"rendered": f"<p>Post {wp_id} Title</p>"},
        "excerpt": {"rendered": excerpt},
        "content": {"rendered": content},
    }


def _mock_wp(posts: dict) -> MagicMock:
    """posts: {wp_id: post dict}. get_post 404s for ids not in the dict."""
    wp = MagicMock()

    async def fake_get_post(wp_post_id):
        if wp_post_id not in posts:
            raise BlogEngineHTTPError(404, "not found")
        return posts[wp_post_id]

    wp.get_post = AsyncMock(side_effect=fake_get_post)
    wp.upload_media = AsyncMock(return_value=555)
    wp.update_post = AsyncMock(
        return_value={"wp_post_id": 0, "wp_url": "https://example.com/p"}
    )
    return wp


def _term_maker(start: int):
    """Sequential {id, name, slug, created} factory for taxonomy mocks."""
    ids = {}

    async def fake(name, parent=0):
        if name not in ids:
            ids[name] = start + len(ids)
        return {
            "id": ids[name],
            "name": name,
            "slug": name.lower().replace(" ", "-"),
            "created": True,
        }

    return fake, ids


# Three rows sharing categories/tags so "once per unique name" is observable.
ROWS = [
    {
        "slug": "post-one",
        "wp_id": 101,
        "category": "Convoso",
        "tags": ["convoso", "automation", "dialer"],
        "excerpt": "keep",
    },
    {
        "slug": "post-two",
        "wp_id": 102,
        "category": "Convoso",
        "tags": ["automation", "reporting", "convoso"],
        "excerpt": "keep",
    },
    {
        "slug": "post-three",
        "wp_id": 103,
        "category": "Games",
        "tags": ["rust", "bevy", "automation"],
        "excerpt": "keep",
    },
]

UNIQUE_TAGS = {"convoso", "automation", "dialer", "reporting", "rust", "bevy"}


def _posts_for(rows):
    return {r["wp_id"]: _fake_post(r["wp_id"]) for r in rows}


# ---------------------------------------------------------------------------
# Dry run: prints one line per post, performs no writes of any kind.
# ---------------------------------------------------------------------------

def test_dry_run_prints_and_touches_nothing(tmp_path, capsys):
    mapping = _write_mapping(tmp_path, ROWS)
    wp = _mock_wp(_posts_for(ROWS))
    cat_mock = AsyncMock()
    tag_mock = AsyncMock()
    render_mock = MagicMock()

    with patch("blog_engine.core.backfill._get_wp_handler", return_value=wp), \
         patch("blog_engine.tools.taxonomy.get_or_create_category", cat_mock), \
         patch("blog_engine.tools.taxonomy.get_or_create_tag", tag_mock), \
         patch("blog_engine.core.featured_image.render", render_mock):
        results = asyncio.run(walk(mapping, dry_run=True))

    out_lines = [l for l in capsys.readouterr().out.splitlines() if " -> " in l]
    assert len(out_lines) == 3
    assert "101 post-one -> lane=consulting category=Convoso" in out_lines[0]
    assert "lane=building category=Games" in out_lines[2]
    for line in out_lines:
        assert "tags=" in line and "excerpt=keep" in line

    wp.update_post.assert_not_called()
    cat_mock.assert_not_called()
    tag_mock.assert_not_called()
    render_mock.assert_not_called()
    assert len(results) == 3
    assert all(r["action"] == "dry-run" for r in results)


# ---------------------------------------------------------------------------
# Apply: terms resolved once per unique name, image rendered and uploaded per
# post, update_post gets categories/tags/featured_media/excerpt — never status.
# ---------------------------------------------------------------------------

def test_apply_resolves_terms_once_and_updates(tmp_path):
    mapping = _write_mapping(tmp_path, ROWS)
    wp = _mock_wp(_posts_for(ROWS))
    cat_fn, cat_ids = _term_maker(100)
    tag_fn, tag_ids = _term_maker(200)
    cat_mock = AsyncMock(side_effect=cat_fn)
    tag_mock = AsyncMock(side_effect=tag_fn)
    render_mock = MagicMock()

    with patch("blog_engine.core.backfill._get_wp_handler", return_value=wp), \
         patch("blog_engine.tools.taxonomy.get_or_create_category", cat_mock), \
         patch("blog_engine.tools.taxonomy.get_or_create_tag", tag_mock), \
         patch("blog_engine.core.featured_image.render", render_mock):
        results = asyncio.run(walk(mapping, dry_run=False))

    # Once per unique name: 2 categories, 6 tags across the 3 rows.
    assert cat_mock.call_count == 2
    assert tag_mock.call_count == len(UNIQUE_TAGS)

    # One rendered image and one upload per post.
    assert render_mock.call_count == 3
    assert wp.upload_media.call_count == 3
    last_render = render_mock.call_args.kwargs
    assert last_render["title"] == "Post 103 Title"
    assert last_render["category"] == "Games"
    assert last_render["lane"] == "building"

    assert wp.update_post.call_count == 3
    for call in wp.update_post.call_args_list:
        fields = call.kwargs["fields"]
        assert "status" not in fields
        assert set(fields) == {"categories", "tags", "featured_media", "excerpt"}
        assert fields["featured_media"] == 555
        assert fields["excerpt"] == "Existing excerpt."
        assert len(fields["categories"]) == 1
        assert len(fields["tags"]) == 3

    # Resolved ids, not names, go to WordPress.
    by_slug = {c.kwargs["post_id"]: c.kwargs["fields"] for c in wp.update_post.call_args_list}
    assert by_slug["post-one"]["categories"] == [cat_ids["Convoso"]]
    assert by_slug["post-three"]["categories"] == [cat_ids["Games"]]
    assert set(by_slug["post-one"]["tags"]) == {
        tag_ids["convoso"], tag_ids["automation"], tag_ids["dialer"]
    }

    assert [r["action"] for r in results] == ["updated"] * 3


# ---------------------------------------------------------------------------
# A row that fails the metadata gate is skipped; the walk continues.
# ---------------------------------------------------------------------------

def test_apply_gate_failure_skips_row_and_continues(tmp_path):
    mapping = _write_mapping(tmp_path, ROWS)
    wp = _mock_wp(_posts_for(ROWS))
    cat_fn, _ = _term_maker(100)
    tag_fn, _ = _term_maker(200)

    def fake_gate(draft):
        if draft["categories"] == ["Games"]:
            return ["has_minimum_tags"]
        return []

    with patch("blog_engine.core.backfill._get_wp_handler", return_value=wp), \
         patch("blog_engine.tools.taxonomy.get_or_create_category",
               AsyncMock(side_effect=cat_fn)), \
         patch("blog_engine.tools.taxonomy.get_or_create_tag",
               AsyncMock(side_effect=tag_fn)), \
         patch("blog_engine.core.featured_image.render", MagicMock()), \
         patch("blog_engine.tools.validate_metadata.check_draft_gate",
               side_effect=fake_gate):
        results = asyncio.run(walk(mapping, dry_run=False))

    updated_ids = {c.kwargs["wp_post_id"] for c in wp.update_post.call_args_list}
    assert updated_ids == {101, 102}

    by_slug = {r["slug"]: r for r in results}
    assert by_slug["post-three"]["action"] == "skipped"
    assert "has_minimum_tags" in by_slug["post-three"]["error"]
    assert by_slug["post-one"]["action"] == "updated"
    assert by_slug["post-two"]["action"] == "updated"


# ---------------------------------------------------------------------------
# update_post raising (e.g. HTTP 403, Contributor lacks edit_published_posts)
# is caught, recorded as "needs manual approval", and the walk continues.
# ---------------------------------------------------------------------------

def test_apply_update_403_needs_manual_approval_and_continues(tmp_path):
    mapping = _write_mapping(tmp_path, ROWS)
    wp = _mock_wp(_posts_for(ROWS))
    cat_fn, _ = _term_maker(100)
    tag_fn, _ = _term_maker(200)

    async def fake_update(post_id, wp_post_id, fields):
        if wp_post_id == 102:
            raise BlogEngineHTTPError(403, "Sorry, you are not allowed to edit this post.")
        return {"wp_post_id": wp_post_id, "wp_url": "https://example.com/p"}

    wp.update_post = AsyncMock(side_effect=fake_update)

    with patch("blog_engine.core.backfill._get_wp_handler", return_value=wp), \
         patch("blog_engine.tools.taxonomy.get_or_create_category",
               AsyncMock(side_effect=cat_fn)), \
         patch("blog_engine.tools.taxonomy.get_or_create_tag",
               AsyncMock(side_effect=tag_fn)), \
         patch("blog_engine.core.featured_image.render", MagicMock()):
        results = asyncio.run(walk(mapping, dry_run=False))

    assert wp.update_post.call_count == 3
    by_slug = {r["slug"]: r for r in results}
    assert by_slug["post-two"]["action"] == "needs manual approval"
    assert "403" in by_slug["post-two"]["error"]
    assert by_slug["post-one"]["action"] == "updated"
    assert by_slug["post-three"]["action"] == "updated"


# ---------------------------------------------------------------------------
# Empty excerpt falls back to the first 30 HTML-stripped words of content.
# ---------------------------------------------------------------------------

def test_apply_excerpt_fallback_first_30_words(tmp_path):
    rows = [{
        "slug": "post-no-excerpt",
        "wp_id": 110,
        "category": "Dev Notes",
        "tags": ["a", "b", "c"],
        "excerpt": "keep",
    }]
    mapping = _write_mapping(tmp_path, rows)

    words = [f"word{i}" for i in range(1, 41)]
    content = "<p>" + " ".join(words) + "</p>"
    wp = _mock_wp({110: _fake_post(110, excerpt="", content=content)})
    cat_fn, _ = _term_maker(100)
    tag_fn, _ = _term_maker(200)

    with patch("blog_engine.core.backfill._get_wp_handler", return_value=wp), \
         patch("blog_engine.tools.taxonomy.get_or_create_category",
               AsyncMock(side_effect=cat_fn)), \
         patch("blog_engine.tools.taxonomy.get_or_create_tag",
               AsyncMock(side_effect=tag_fn)), \
         patch("blog_engine.core.featured_image.render", MagicMock()):
        results = asyncio.run(walk(mapping, dry_run=False))

    fields = wp.update_post.call_args.kwargs["fields"]
    assert fields["excerpt"] == " ".join(words[:30])
    assert results[0]["action"] == "updated"


# ---------------------------------------------------------------------------
# A mapping row whose live post 404s is skipped with a warning, not fatal.
# ---------------------------------------------------------------------------

def test_apply_missing_post_is_skipped(tmp_path):
    mapping = _write_mapping(tmp_path, ROWS)
    posts = _posts_for(ROWS)
    del posts[102]  # post-two was deleted since the mapping was drafted
    wp = _mock_wp(posts)
    cat_fn, _ = _term_maker(100)
    tag_fn, _ = _term_maker(200)

    with patch("blog_engine.core.backfill._get_wp_handler", return_value=wp), \
         patch("blog_engine.tools.taxonomy.get_or_create_category",
               AsyncMock(side_effect=cat_fn)), \
         patch("blog_engine.tools.taxonomy.get_or_create_tag",
               AsyncMock(side_effect=tag_fn)), \
         patch("blog_engine.core.featured_image.render", MagicMock()):
        results = asyncio.run(walk(mapping, dry_run=False))

    updated_ids = {c.kwargs["wp_post_id"] for c in wp.update_post.call_args_list}
    assert updated_ids == {101, 103}
    by_slug = {r["slug"]: r for r in results}
    assert by_slug["post-two"]["action"] == "skipped"
    assert "404" in by_slug["post-two"]["error"]

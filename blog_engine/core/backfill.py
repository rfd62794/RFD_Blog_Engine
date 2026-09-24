"""
blog_engine/core/backfill.py

Walk every row of data/backfill_mapping.yaml (drafted by Claude, approved by
Robert) and give each existing WordPress post a lane-derived featured image,
its new lane category, its tags, and an excerpt where it has none.

Built per docs/directives/Blog_Backfill_Directive.md. Apply mode submits each
post as an update with no "status" field — the live post's status is never
touched, and a Contributor credential that lacks edit_published_posts gets a
403, which is caught and recorded as "needs manual approval" rather than
raised.
"""

import os
import re
import tempfile
from pathlib import Path

import yaml

from blog_engine.core import lanes, featured_image
from blog_engine.infra.db_manager import DBManager
from blog_engine.infra.logger import get_logger
from blog_engine.api.wordpress import WordPressHandler
from blog_engine.infra.base_api_handler import BlogEngineHTTPError
from blog_engine.tools import taxonomy, validate_metadata

logger = get_logger(__name__)


def _get_wp_handler() -> WordPressHandler:
    """Construct the WordPress handler the same way every tool module does."""
    wp_url = os.getenv("WORDPRESS_URL", "").rstrip("/")
    wp_user = os.getenv("WORDPRESS_USER", "")
    wp_pass = os.getenv("WORDPRESS_APP_PASSWORD", "")
    db = DBManager()
    return WordPressHandler(db, wp_url, wp_user, wp_pass)


def _plain_text(rendered: str) -> str:
    """Strip HTML tags and collapse whitespace from a rendered WP field."""
    return " ".join(re.sub(r"<[^>]+>", "", rendered or "").split())


def _excerpt_for(post: dict) -> str:
    """
    Existing excerpt if non-empty (HTML-stripped, whitespace-collapsed),
    else the first 30 words of the post's rendered content.
    """
    existing = _plain_text(post.get("excerpt", {}).get("rendered", ""))
    if existing:
        return existing
    words = _plain_text(post.get("content", {}).get("rendered", "")).split()
    return " ".join(words[:30])


async def walk(mapping_path: str, dry_run: bool) -> list[dict]:
    """
    Load mapping_path (YAML, schema in data/backfill_mapping.yaml). For each
    row:
      1. Fetch the live post via wp.get_post(wp_id) — skip with a logged
         warning if the fetch 404s (post deleted since the mapping was
         drafted).
      2. lane = lanes.lane_for([row["category"]]).
      3. If dry_run: print one line per post and continue — no HTTP writes,
         no get_or_create_category/tag calls (those can create WP terms even
         on a "read"), no featured_image.render call.
      4. Otherwise (apply): resolve category and tag names to WP ids, render
         and upload the featured image, build the excerpt, gate the fields
         with validate_metadata.check_draft_gate, and update the post — a
         403-style update failure is logged as "needs manual approval" and
         the walk continues.
      5. Return a list of per-post result dicts for the CLI summary.
    """
    with open(mapping_path, "r", encoding="utf-8") as f:
        mapping = yaml.safe_load(f)
    rows = (mapping or {}).get("posts") or []

    wp = _get_wp_handler()
    results = []
    # Resolved-term caches: one get_or_create call per unique name per run.
    category_cache: dict[str, dict] = {}
    tag_cache: dict[str, dict] = {}

    for row in rows:
        slug = row["slug"]
        wp_id = row["wp_id"]
        category_name = row["category"]
        result = {"slug": slug, "wp_id": wp_id}

        # 1. Fetch the live post
        try:
            post = await wp.get_post(wp_id)
        except BlogEngineHTTPError as e:
            if e.status_code == 404:
                logger.warning("backfill.post_missing", slug=slug, wp_id=wp_id)
                result.update(action="skipped", error=f"post {wp_id} not found (404)")
            else:
                logger.error("backfill.fetch_failed", slug=slug, wp_id=wp_id, error=str(e))
                result.update(action="skipped", error=str(e))
            results.append(result)
            continue
        except Exception as e:
            logger.error("backfill.fetch_failed", slug=slug, wp_id=wp_id, error=str(e))
            result.update(action="skipped", error=str(e))
            results.append(result)
            continue

        # 2. Lane comes from lanes.py, not the mapping — warn if they disagree.
        lane = lanes.lane_for([category_name])
        if row.get("lane") is not None and row["lane"] != lane:
            print(
                f"warning: {slug} mapping lane={row['lane']} disagrees with "
                f"lanes.py lane={lane}; using lanes.py"
            )

        # 3. Dry run: print the planned change, touch nothing.
        if dry_run:
            print(
                f"{wp_id} {slug} -> lane={lane} category={category_name} "
                f"tags={row['tags']} excerpt={row['excerpt']}"
            )
            result.update(
                action="dry-run",
                lane=lane,
                category=category_name,
                tags=row["tags"],
                excerpt=row["excerpt"],
            )
            results.append(result)
            continue

        # 4a-b. Resolve category and tag names to WP ids, creating if missing.
        cat_key = str(category_name).strip().lower()
        if cat_key not in category_cache:
            category_cache[cat_key] = await taxonomy.get_or_create_category(category_name)
        category = category_cache[cat_key]

        tag_results = []
        for tag_name in row["tags"]:
            tag_key = str(tag_name).strip().lower()
            if tag_key not in tag_cache:
                tag_cache[tag_key] = await taxonomy.get_or_create_tag(tag_name)
            tag_results.append(tag_cache[tag_key])

        # 4c. Render and upload the featured image — same pattern as
        # Publisher.publish_wordpress step 2, minus the draft persist.
        title = _plain_text(post.get("title", {}).get("rendered", "")) or slug
        fd, tmp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        try:
            featured_image.render(
                title=title,
                category=category_name,
                lane=lane,
                out_path=tmp_path,
            )
            media_id = await wp.upload_media(path=tmp_path, alt=title)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        # 4d-e. Excerpt and fields — deliberately no "status" key.
        excerpt = _excerpt_for(post)
        fields = {
            "categories": [category["id"]],
            "tags": [t["id"] for t in tag_results],
            "featured_media": media_id,
            "excerpt": excerpt,
        }

        # 4f. Hard metadata gate — a bad row skips, it does not stop the walk.
        gate_failures = validate_metadata.check_draft_gate({
            "featured_media_id": media_id,
            "categories": [category_name],
            "tags": row["tags"],
        })
        if gate_failures:
            logger.warning(
                "backfill.gate_failed",
                slug=slug,
                wp_id=wp_id,
                failures=gate_failures,
            )
            result.update(action="skipped", error=f"gate failed: {', '.join(gate_failures)}")
            results.append(result)
            continue

        # 4g-h. Update the post. A 403 (Contributor lacks
        # edit_published_posts on a live post) is the expected "pending
        # revision" outcome — record it, keep walking.
        try:
            await wp.update_post(post_id=slug, wp_post_id=wp_id, fields=fields)
        except Exception as e:
            logger.warning(f"post {wp_id} needs manual approval: {e}")
            result.update(action="needs manual approval", error=str(e))
            results.append(result)
            continue

        result.update(action="updated")
        results.append(result)

    return results

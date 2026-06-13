"""
blog_engine/tools/calendar.py

Calendar management tools for rfd-blog-engine.
"""

import os
from pathlib import Path
import yaml

from blog_engine.infra.db_manager import DBManager
from blog_engine.infra.logger import get_logger
from blog_engine.api.wordpress import WordPressHandler
from blog_engine.core.inventory import InventoryManager, INVENTORY_DIR

logger = get_logger(__name__)


def _get_wp_handler() -> WordPressHandler:
    wp_url = os.getenv("WORDPRESS_URL", "").rstrip("/")
    wp_user = os.getenv("WORDPRESS_USER", "")
    wp_pass = os.getenv("WORDPRESS_APP_PASSWORD", "")
    db = DBManager()
    return WordPressHandler(db, wp_url, wp_user, wp_pass)


async def reschedule_post(post_id: str, new_date: str) -> dict:
    """
    Atomically reschedule a post: updates WordPress date AND inventory YAML.

    post_id: engine post ID (e.g. 'dev-020') — never a raw WordPress integer.
    new_date: ISO 8601 string e.g. '2026-10-29T09:00:00'.

    Rules:
    - If WordPress call fails, inventory YAML is not touched.
    - If YAML write fails after successful WP update, logs inconsistency and raises.
    - Raises ValueError if post_id not found or wp_post_id missing from inventory.

    Returns: {post_id, wp_post_id, old_date, new_date, status: 'rescheduled'}
    """
    inventory = InventoryManager()
    post = inventory.get_post(post_id)
    if post is None:
        raise ValueError(f"Post not found in inventory: {post_id}")

    wp_post_id = post.get("wp_post_id")
    if not wp_post_id:
        raise ValueError(f"No wp_post_id in inventory for {post_id} — publish to WordPress first")

    old_date = post.get("scheduled_date")

    # Step 1: WordPress update (if this fails, YAML is never touched)
    wp = _get_wp_handler()
    await wp.update_post(
        post_id=post_id,
        wp_post_id=int(wp_post_id),
        fields={"date": new_date, "status": "future"},
    )

    # Step 2: YAML update (atomic write via tmp file)
    path = inventory.inventory_dir / f"{post_id}.yaml"
    post["scheduled_date"] = new_date

    tmp_path = path.with_suffix(".yaml.tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(post, f, sort_keys=False, allow_unicode=True)
        tmp_path.replace(path)
    except Exception as e:
        logger.error(
            "reschedule.yaml_write_failed",
            post_id=post_id,
            wp_post_id=wp_post_id,
            new_date=new_date,
            error=str(e),
        )
        raise RuntimeError(
            f"WordPress was updated to {new_date} but inventory YAML write failed for {post_id}: {e}. "
            f"Manual YAML correction required."
        ) from e

    logger.info("reschedule.complete", post_id=post_id, wp_post_id=wp_post_id, old_date=old_date, new_date=new_date)

    return {
        "post_id": post_id,
        "wp_post_id": int(wp_post_id),
        "old_date": old_date,
        "new_date": new_date,
        "status": "rescheduled",
    }


async def get_full_calendar(status_filter: str = None) -> list:
    """
    Return all posts sorted by scheduled_date ascending, nulls last.
    Reads only from inventory YAMLs — no live WordPress API calls.

    status_filter: optional, e.g. 'approved'. If provided, excludes non-matching posts.
    Posts with no scheduled_date are included but sorted last.

    Returns list of {post_id, title, status, category, scheduled_date, wp_post_id}.
    """
    inventory = InventoryManager()
    posts = inventory.load()

    if status_filter is not None:
        posts = [p for p in posts if p.get("status") == status_filter]

    def sort_key(p):
        d = p.get("scheduled_date")
        if d is None:
            return (1, "")
        return (0, str(d))

    posts.sort(key=sort_key)

    return [
        {
            "post_id": p.get("post_id"),
            "title": p.get("title"),
            "status": p.get("status"),
            "category": p.get("category"),
            "scheduled_date": p.get("scheduled_date"),
            "wp_post_id": p.get("wp_post_id"),
        }
        for p in posts
    ]


def register_calendar_tools(mcp):
    """Register calendar tools with FastMCP server."""
    mcp.tool()(reschedule_post)
    mcp.tool()(get_full_calendar)

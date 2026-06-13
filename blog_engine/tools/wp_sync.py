"""
blog_engine/tools/wp_sync.py

WordPress sync tools for rfd-blog-engine.

Provides lookup, listing, inventory patching, and pre-engine post import.
"""

import os
from datetime import datetime, timezone
from pathlib import Path
import yaml

from blog_engine.infra.db_manager import DBManager
from blog_engine.infra.logger import get_logger
from blog_engine.api.wordpress import WordPressHandler
from blog_engine.core.inventory import InventoryManager, INVENTORY_DIR

logger = get_logger(__name__)

_UPDATE_INVENTORY_ALLOWLIST = {
    "wp_post_id",
    "scheduled_date",
    "category",
    "notes",
    "tags",
    "title",
}


def _get_wp_handler() -> WordPressHandler:
    wp_url = os.getenv("WORDPRESS_URL", "").rstrip("/")
    wp_user = os.getenv("WORDPRESS_USER", "")
    wp_pass = os.getenv("WORDPRESS_APP_PASSWORD", "")
    db = DBManager()
    return WordPressHandler(db, wp_url, wp_user, wp_pass)


async def get_wordpress_post_by_slug(slug: str) -> dict:
    """
    Look up a WordPress post by its slug.

    Uses GET /wp/v2/posts?slug={slug}&_fields=id,date,status,title,slug.
    Raises ValueError if no post found with that slug.
    Returns {id, date, status, title, slug}.
    """
    wp = _get_wp_handler()
    url = f"{wp.base_url}/wp-json/wp/v2/posts"
    params = {"slug": slug, "status": "any", "_fields": "id,date,status,title,slug", "per_page": 1}

    response = await wp._make_request(
        method="GET",
        url=url,
        auth=wp.auth,
        params=params,
    )
    posts = response.json()

    if not isinstance(posts, list) or len(posts) == 0:
        raise ValueError(f"No WordPress post found with slug: {slug}")

    p = posts[0]
    return {
        "id": p.get("id"),
        "date": p.get("date"),
        "status": p.get("status"),
        "title": p.get("title", {}).get("rendered", "") if isinstance(p.get("title"), dict) else p.get("title", ""),
        "slug": p.get("slug"),
    }


async def list_wordpress_posts(status: str = None, per_page: int = 100) -> list:
    """
    List WordPress posts with optional status filter.

    Returns list of {id, date, status, title, slug}.
    If the response length equals per_page, appends {"truncated": True} as
    the final item to signal the caller that results may be incomplete.
    """
    wp = _get_wp_handler()
    url = f"{wp.base_url}/wp-json/wp/v2/posts"
    params: dict = {"per_page": per_page, "status": status if status is not None else "any", "_fields": "id,date,status,title,slug"}

    response = await wp._make_request(
        method="GET",
        url=url,
        auth=wp.auth,
        params=params,
    )
    raw = response.json()

    results = [
        {
            "id": p.get("id"),
            "date": p.get("date"),
            "status": p.get("status"),
            "title": p.get("title", {}).get("rendered", "") if isinstance(p.get("title"), dict) else p.get("title", ""),
            "slug": p.get("slug"),
        }
        for p in raw
    ]

    if len(results) == per_page:
        results.append({"truncated": True})

    return results


async def update_inventory_fields(post_id: str, fields: dict) -> dict:
    """
    Patch arbitrary fields on an inventory YAML entry.

    Writable fields: wp_post_id, scheduled_date, category, notes, tags, title.
    Raises ValueError on unknown key or missing post_id.
    Atomic write — temp file then replace.
    Returns the full updated inventory dict.
    """
    unknown = set(fields.keys()) - _UPDATE_INVENTORY_ALLOWLIST
    if unknown:
        raise ValueError(
            f"Unknown inventory field(s): {sorted(unknown)}. "
            f"Writable fields: {sorted(_UPDATE_INVENTORY_ALLOWLIST)}"
        )

    inventory = InventoryManager()
    post = inventory.get_post(post_id)
    if post is None:
        raise ValueError(f"Post not found in inventory: {post_id}")

    post.update(fields)

    path = inventory.inventory_dir / f"{post_id}.yaml"
    tmp_path = path.with_suffix(".yaml.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(post, f, sort_keys=False, allow_unicode=True)
    tmp_path.replace(path)

    logger.info("inventory.fields_updated", post_id=post_id, fields=list(fields.keys()))
    return post


async def import_wordpress_post(wp_post_id: int, post_id: str) -> dict:
    """
    Import a pre-engine WordPress post into the inventory.

    Creates data/inventory/{post_id}.yaml with status: imported.
    Raises ValueError if post_id already exists or WP post not found.
    Never overwrites — use update_inventory_fields for existing entries.
    """
    inventory = InventoryManager()
    path = inventory.inventory_dir / f"{post_id}.yaml"
    if path.exists():
        raise ValueError(
            f"Inventory entry already exists for {post_id}. "
            f"Use update_inventory_fields to modify existing entries."
        )

    # Fetch WP post
    wp = _get_wp_handler()
    wp_post = await wp.get_post(wp_post_id)
    if not wp_post or wp_post.get("id") is None:
        raise ValueError(f"WordPress post not found: wp_post_id={wp_post_id}")

    title = wp_post.get("title", {}).get("rendered", "") if isinstance(wp_post.get("title"), dict) else str(wp_post.get("title", ""))
    scheduled_date = wp_post.get("date", "")

    data = {
        "post_id": post_id,
        "title": title,
        "status": "imported",
        "category": "",
        "notes": "",
        "tags": [],
        "wp_post_id": wp_post_id,
        "scheduled_date": scheduled_date,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    tmp_path = path.with_suffix(".yaml.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
    tmp_path.replace(path)

    logger.info("inventory.imported", post_id=post_id, wp_post_id=wp_post_id, title=title)
    return data


def register_wp_sync_tools(mcp):
    """Register wp_sync tools with FastMCP server."""
    mcp.tool()(get_wordpress_post_by_slug)
    mcp.tool()(list_wordpress_posts)
    mcp.tool()(update_inventory_fields)
    mcp.tool()(import_wordpress_post)

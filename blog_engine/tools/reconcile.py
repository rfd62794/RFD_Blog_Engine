"""
blog_engine/tools/reconcile.py

Inventory reconciliation tools for rfd-blog-engine.
"""

import html
import os
import re

import yaml

from blog_engine.infra.db_manager import DBManager
from blog_engine.infra.logger import get_logger
from blog_engine.api.wordpress import WordPressHandler
from blog_engine.core.inventory import InventoryManager

logger = get_logger(__name__)

_BULK_ALLOWLIST = {
    "wp_post_id",
    "scheduled_date",
    "category",
    "notes",
    "tags",
    "title",
}


def _normalize_title(title: str) -> str:
    title = html.unescape(title)
    title = title.lower()
    title = re.sub(r'[^a-z0-9\s]', '', title)
    title = re.sub(r'\s+', ' ', title).strip()
    return title


def _get_wp_handler() -> WordPressHandler:
    wp_url = os.getenv("WORDPRESS_URL", "").rstrip("/")
    wp_user = os.getenv("WORDPRESS_USER", "")
    wp_pass = os.getenv("WORDPRESS_APP_PASSWORD", "")
    db = DBManager()
    return WordPressHandler(db, wp_url, wp_user, wp_pass)


async def reconcile_wp_post_ids(dry_run: bool = False) -> dict:
    """
    Match inventory posts to WordPress posts by normalized title and
    backfill wp_post_id into inventory YAMLs.

    dry_run=True: preview only — no YAML writes.
    Never overwrites an existing non-null wp_post_id.

    Returns:
      {
        matched: [{post_id, wp_post_id, title}],
        unmatched_inventory: [{post_id, title}],
        unmatched_wp: [{wp_post_id, title}],
        dry_run: bool
      }
    """
    inventory = InventoryManager()
    all_posts = inventory.load()

    # Fetch all WP posts (status=any to include scheduled)
    wp = _get_wp_handler()
    url = f"{wp.base_url}/wp-json/wp/v2/posts"
    params = {"per_page": 100, "status": "any", "_fields": "id,date,status,title,slug"}
    response = await wp._make_request(method="GET", url=url, auth=wp.auth, params=params)
    wp_posts = response.json()

    # Build WP lookup: normalized_title → post dict
    wp_by_title: dict[str, dict] = {}
    for wp_post in wp_posts:
        raw_title = wp_post.get("title", "")
        if isinstance(raw_title, dict):
            raw_title = raw_title.get("rendered", "")
        norm = _normalize_title(raw_title)
        wp_by_title[norm] = {"id": wp_post["id"], "title": raw_title, "slug": wp_post.get("slug", "")}

    matched = []
    unmatched_inventory = []
    wp_matched_ids = set()

    for post in all_posts:
        # Skip posts that already have a wp_post_id
        if post.get("wp_post_id"):
            continue

        inv_title = post.get("title", "")
        norm = _normalize_title(inv_title)
        wp_match = wp_by_title.get(norm)

        if wp_match is None:
            unmatched_inventory.append({"post_id": post["post_id"], "title": inv_title})
            continue

        wp_id = wp_match["id"]
        wp_matched_ids.add(wp_id)
        matched.append({"post_id": post["post_id"], "wp_post_id": wp_id, "title": inv_title})

        if not dry_run:
            path = inventory.inventory_dir / f"{post['post_id']}.yaml"
            post["wp_post_id"] = wp_id
            tmp_path = path.with_suffix(".yaml.tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(post, f, sort_keys=False, allow_unicode=True)
            tmp_path.replace(path)
            logger.info("reconcile.wp_id_written", post_id=post["post_id"], wp_post_id=wp_id)

    # WP posts that had no inventory match
    unmatched_wp = [
        {"wp_post_id": wp_post["id"], "title": wp_by_title[_normalize_title(
            wp_post.get("title", {}).get("rendered", "") if isinstance(wp_post.get("title"), dict)
            else wp_post.get("title", "")
        )]["title"]}
        for wp_post in wp_posts
        if wp_post["id"] not in wp_matched_ids
        # Also exclude WP posts whose IDs are already in inventory
        and wp_post["id"] not in {p.get("wp_post_id") for p in all_posts}
    ]

    logger.info(
        "reconcile.complete",
        matched=len(matched),
        unmatched_inventory=len(unmatched_inventory),
        unmatched_wp=len(unmatched_wp),
        dry_run=dry_run,
    )

    return {
        "matched": matched,
        "unmatched_inventory": unmatched_inventory,
        "unmatched_wp": unmatched_wp,
        "dry_run": dry_run,
    }


async def bulk_update_inventory(updates: list) -> dict:
    """
    Apply multiple inventory field updates in one call.

    Each item in updates: {"post_id": str, "fields": dict}.
    Validates ALL post_ids exist and ALL field keys are in the allowlist
    before writing any YAML. Raises ValueError on first violation.

    Per-entry write failures are logged and counted but do not abort
    remaining entries.

    Returns {updated: int, failed: int, errors: list[str]}.
    """
    inventory = InventoryManager()

    # Validate all post_ids and field keys before touching anything
    for item in updates:
        post_id = item.get("post_id")
        fields = item.get("fields", {})

        if inventory.get_post(post_id) is None:
            raise ValueError(f"Post not found in inventory: {post_id}")

        unknown = set(fields.keys()) - _BULK_ALLOWLIST
        if unknown:
            raise ValueError(
                f"Unknown field(s) for {post_id}: {sorted(unknown)}. "
                f"Allowed: {sorted(_BULK_ALLOWLIST)}"
            )

    # All valid — apply writes
    updated = 0
    failed = 0
    errors = []

    for item in updates:
        post_id = item["post_id"]
        fields = item["fields"]
        try:
            post = inventory.get_post(post_id)
            post.update(fields)
            path = inventory.inventory_dir / f"{post_id}.yaml"
            tmp_path = path.with_suffix(".yaml.tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(post, f, sort_keys=False, allow_unicode=True)
            tmp_path.replace(path)
            updated += 1
            logger.info("bulk_update.written", post_id=post_id, fields=list(fields.keys()))
        except Exception as e:
            failed += 1
            msg = f"{post_id}: {e}"
            errors.append(msg)
            logger.error("bulk_update.failed", post_id=post_id, error=str(e))

    return {"updated": updated, "failed": failed, "errors": errors}


def register_reconcile_tools(mcp):
    """Register reconciliation tools with FastMCP server."""
    mcp.tool()(reconcile_wp_post_ids)
    mcp.tool()(bulk_update_inventory)

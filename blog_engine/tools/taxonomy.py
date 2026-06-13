"""
blog_engine/tools/taxonomy.py

WordPress taxonomy tools for rfd-blog-engine.

Provides tag/category listing, get-or-create, and full taxonomy assignment
on a post (resolves names → IDs, updates WordPress + inventory YAML).
"""

import html
import os
import yaml

from blog_engine.infra.db_manager import DBManager
from blog_engine.infra.logger import get_logger
from blog_engine.api.wordpress import WordPressHandler
from blog_engine.core.inventory import InventoryManager

logger = get_logger(__name__)


def _get_wp_handler() -> WordPressHandler:
    wp_url = os.getenv("WORDPRESS_URL", "").rstrip("/")
    wp_user = os.getenv("WORDPRESS_USER", "")
    wp_pass = os.getenv("WORDPRESS_APP_PASSWORD", "")
    db = DBManager()
    return WordPressHandler(db, wp_url, wp_user, wp_pass)


async def list_wordpress_tags() -> list:
    """
    List all WordPress tags.

    Returns list of {id, name, slug, count}.
    Appends {"truncated": True} if response length equals 100.
    """
    wp = _get_wp_handler()
    url = f"{wp.base_url}/wp-json/wp/v2/tags"
    params = {"per_page": 100, "_fields": "id,name,slug,count"}

    response = await wp._make_request(
        method="GET",
        url=url,
        auth=wp.auth,
        params=params,
    )
    raw = response.json()

    results = [
        {"id": t["id"], "name": t["name"], "slug": t["slug"], "count": t.get("count", 0)}
        for t in raw
    ]

    if len(results) == 100:
        results.append({"truncated": True})

    return results


async def list_wordpress_categories() -> list:
    """
    List all WordPress categories.

    Returns list of {id, name, slug, count}.
    Appends {"truncated": True} if response length equals 100.
    """
    wp = _get_wp_handler()
    url = f"{wp.base_url}/wp-json/wp/v2/categories"
    params = {"per_page": 100, "_fields": "id,name,slug,count"}

    response = await wp._make_request(
        method="GET",
        url=url,
        auth=wp.auth,
        params=params,
    )
    raw = response.json()

    results = [
        {"id": c["id"], "name": c["name"], "slug": c["slug"], "count": c.get("count", 0)}
        for c in raw
    ]

    if len(results) == 100:
        results.append({"truncated": True})

    return results


async def get_or_create_tag(name: str) -> dict:
    """
    Return an existing WordPress tag by name (case-insensitive), or create it.

    Returns {id, name, slug, created: bool}.
    created=False if tag already existed, created=True if newly created.
    """
    tags = await list_wordpress_tags()
    name_lower = name.lower()

    for tag in tags:
        if isinstance(tag.get("id"), int) and html.unescape(tag["name"]).lower() == name_lower:
            return {"id": tag["id"], "name": tag["name"], "slug": tag["slug"], "created": False}

    wp = _get_wp_handler()
    url = f"{wp.base_url}/wp-json/wp/v2/tags"

    response = await wp._make_request(
        method="POST",
        url=url,
        auth=wp.auth,
        json={"name": name},
    )
    created = response.json()
    logger.info("taxonomy.tag_created", name=name, id=created["id"])
    return {"id": created["id"], "name": created["name"], "slug": created["slug"], "created": True}


async def get_or_create_category(name: str, parent: int = 0) -> dict:
    """
    Return an existing WordPress category by name (case-insensitive), or create it.

    parent=0 means top-level. Returns {id, name, slug, created: bool}.
    """
    categories = await list_wordpress_categories()
    name_lower = name.lower()

    for cat in categories:
        if isinstance(cat.get("id"), int) and html.unescape(cat["name"]).lower() == name_lower:
            return {"id": cat["id"], "name": cat["name"], "slug": cat["slug"], "created": False}

    wp = _get_wp_handler()
    url = f"{wp.base_url}/wp-json/wp/v2/categories"

    response = await wp._make_request(
        method="POST",
        url=url,
        auth=wp.auth,
        json={"name": name, "parent": parent},
    )
    created = response.json()
    logger.info("taxonomy.category_created", name=name, id=created["id"])
    return {"id": created["id"], "name": created["name"], "slug": created["slug"], "created": True}


async def set_post_taxonomy(
    post_id: str,
    tags: list = None,
    categories: list = None,
) -> dict:
    """
    Assign tags and/or categories to a post by engine post_id.

    tags and categories are lists of name strings — IDs are resolved internally.
    Updates WordPress first, then inventory YAML.
    Raises ValueError if both are None, post_id missing, or wp_post_id missing.
    Raises RuntimeError if YAML write fails after successful WP update.

    Returns {post_id, wp_post_id, tags_set, categories_set,
             new_tags_created, new_categories_created}.
    """
    if tags is None and categories is None:
        raise ValueError("At least one of tags or categories must be provided.")

    inventory = InventoryManager()
    post = inventory.get_post(post_id)
    if post is None:
        raise ValueError(f"Post not found in inventory: {post_id}")

    wp_post_id = post.get("wp_post_id")
    if not wp_post_id:
        raise ValueError(f"No wp_post_id in inventory for {post_id} — publish to WordPress first.")

    tag_ids = []
    resolved_tag_names = []
    new_tags_created = []

    if tags is not None:
        for name in tags:
            result = await get_or_create_tag(name)
            tag_ids.append(result["id"])
            resolved_tag_names.append(result["name"])
            if result["created"]:
                new_tags_created.append(result["name"])

    category_ids = []
    resolved_category_names = []
    new_categories_created = []

    if categories is not None:
        for name in categories:
            result = await get_or_create_category(name)
            category_ids.append(result["id"])
            resolved_category_names.append(result["name"])
            if result["created"]:
                new_categories_created.append(result["name"])

    # WordPress update first
    wp = _get_wp_handler()
    fields = {}
    if tag_ids:
        fields["tags"] = tag_ids
    if category_ids:
        fields["categories"] = category_ids

    await wp.update_post(
        post_id=post_id,
        wp_post_id=int(wp_post_id),
        fields=fields,
    )

    # Inventory YAML update — atomic write, non-silent on failure
    if tags is not None:
        post["tags"] = resolved_tag_names
    if categories is not None:
        post["category"] = resolved_category_names[0] if len(resolved_category_names) == 1 else resolved_category_names

    path = inventory.inventory_dir / f"{post_id}.yaml"
    tmp_path = path.with_suffix(".yaml.tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(post, f, sort_keys=False, allow_unicode=True)
        tmp_path.replace(path)
    except Exception as e:
        logger.error(
            "taxonomy.yaml_write_failed",
            post_id=post_id,
            error=str(e),
        )
        raise RuntimeError(
            f"WordPress taxonomy was updated but inventory YAML write failed for {post_id}: {e}. "
            f"Manual YAML correction required."
        ) from e

    logger.info(
        "taxonomy.set_complete",
        post_id=post_id,
        wp_post_id=wp_post_id,
        tags=resolved_tag_names,
        categories=resolved_category_names,
    )

    return {
        "post_id": post_id,
        "wp_post_id": int(wp_post_id),
        "tags_set": resolved_tag_names,
        "categories_set": resolved_category_names,
        "new_tags_created": new_tags_created,
        "new_categories_created": new_categories_created,
    }


def register_taxonomy_tools(mcp):
    """Register taxonomy tools with FastMCP server."""
    mcp.tool()(list_wordpress_tags)
    mcp.tool()(list_wordpress_categories)
    mcp.tool()(get_or_create_tag)
    mcp.tool()(get_or_create_category)
    mcp.tool()(set_post_taxonomy)

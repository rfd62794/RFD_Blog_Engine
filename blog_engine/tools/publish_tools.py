"""
blog_engine/tools/publish_tools.py

MCP tools for publishing and thread management.
"""

import os
from blog_engine.infra.db_manager import DBManager
from blog_engine.infra.logger import get_logger
from blog_engine.core.inventory import InventoryManager
from blog_engine.core.draft_manager import DraftManager
from blog_engine.core.publisher import Publisher
from blog_engine.api.wordpress import WordPressHandler
from blog_engine.api.devto import DevToHandler

logger = get_logger(__name__)


def _get_wp_handler() -> WordPressHandler:
    """
    Factory function to instantiate WordPressHandler for WordPress-only operations.
    Reads credentials from environment variables.
    Raises EnvironmentError if any required credential is missing.
    """
    wp_url = os.getenv("WORDPRESS_URL")
    wp_user = os.getenv("WORDPRESS_USER")
    wp_app_password = os.getenv("WORDPRESS_APP_PASSWORD")

    missing = []
    if not wp_url:
        missing.append("WORDPRESS_URL")
    if not wp_user:
        missing.append("WORDPRESS_USER")
    if not wp_app_password:
        missing.append("WORDPRESS_APP_PASSWORD")

    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    db = DBManager()
    return WordPressHandler(db, wp_url, wp_user, wp_app_password)


def _get_publisher() -> Publisher:
    """
    Factory function to instantiate Publisher with all dependencies.
    Reads credentials from environment variables.
    Raises EnvironmentError if any required credential is missing.
    """
    wp_url = os.getenv("WORDPRESS_URL")
    wp_user = os.getenv("WORDPRESS_USER")
    wp_app_password = os.getenv("WORDPRESS_APP_PASSWORD")
    devto_api_key = os.getenv("DEVTO_API_KEY")
    
    missing = []
    if not wp_url:
        missing.append("WORDPRESS_URL")
    if not wp_user:
        missing.append("WORDPRESS_USER")
    if not wp_app_password:
        missing.append("WORDPRESS_APP_PASSWORD")
    if not devto_api_key:
        missing.append("DEVTO_API_KEY")
    
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}"
        )
    
    db = DBManager()
    draft_manager = DraftManager(db)
    inventory = InventoryManager()
    wp_handler = WordPressHandler(db, wp_url, wp_user, wp_app_password)
    devto_handler = DevToHandler(db, devto_api_key)
    
    return Publisher(db, draft_manager, inventory, wp_handler, devto_handler)


async def publish_to_wordpress(post_id: str, publish: bool = False, scheduled_date: str = None) -> dict:
    """
    Publish approved draft to WordPress.
    Draft must have status: approved. Calls approval gate.
    publish=False creates WP draft. publish=True publishes immediately.
    scheduled_date="2026-06-14T09:00:00" schedules for future publish.
    If scheduled_date not provided, falls back to scheduled_date from inventory YAML.
    scheduled_date overrides publish parameter when provided.
    Returns: {post_id, wp_post_id, wp_url, status}
    On error: {"error": str(e), "post_id": post_id}
    """
    try:
        # Fallback: read scheduled_date from inventory if not explicitly passed
        if scheduled_date is None:
            try:
                inventory = InventoryManager()
                post = inventory.get_post(post_id)
                if post:
                    scheduled_date = post.get("scheduled_date")
            except Exception:
                pass  # Fallback gracefully — inventory lookup failure is non-fatal

        publisher = _get_publisher()
        return await publisher.publish_wordpress(post_id, publish=publish, scheduled_date=scheduled_date)
    except Exception as e:
        logger.error("publish_to_wordpress.error", post_id=post_id, error=str(e))
        return {"error": str(e), "post_id": post_id}


async def publish_to_devto(post_id: str, published: bool = False) -> dict:
    """
    Syndicate approved draft to Dev.to.
    WordPress must be published first (wp_url required on draft).
    canonical_url set automatically to wp_url.
    Returns: {post_id, devto_id, devto_url, canonical_url}
    On error: {"error": str(e), "post_id": post_id}
    """
    try:
        publisher = _get_publisher()
        return await publisher.publish_devto(post_id, published=published)
    except Exception as e:
        logger.error("publish_to_devto.error", post_id=post_id, error=str(e))
        return {"error": str(e), "post_id": post_id}


async def update_devto_post(
    devto_id: int,
    body_markdown: str = None,
    title: str = None,
    published: bool = None,
    tags: list = None
) -> dict:
    """
    Update an existing Dev.to article via PATCH endpoint.

    Only fields provided are updated. Returns {devto_id, devto_url, status} on success.
    Returns {error, devto_id} on failure.
    """
    try:
        api_key = os.getenv("DEVTO_API_KEY", "")
        if not api_key:
            return {"error": "DEVTO_API_KEY not configured", "devto_id": devto_id}

        url = f"https://dev.to/api/articles/{devto_id}"
        headers = {
            "api-key": api_key,
            "Content-Type": "application/json"
        }

        fields = {}
        if body_markdown is not None:
            fields["body_markdown"] = body_markdown
        if title is not None:
            fields["title"] = title
        if published is not None:
            fields["published"] = published
        if tags is not None:
            fields["tags"] = tags

        db = DBManager()
        devto_handler = DevToHandler(db, api_key)

        response = await devto_handler._make_request(
            method="PATCH",
            url=url,
            headers=headers,
            json={"article": fields}
        )

        data = response.json()
        devto_url = data.get("url", "")

        logger.info("update_devto_post.success", devto_id=devto_id)

        return {
            "devto_id": devto_id,
            "devto_url": devto_url,
            "status": "updated"
        }

    except Exception as e:
        logger.error("update_devto_post.error", devto_id=devto_id, error=str(e))
        return {"error": str(e), "devto_id": devto_id}


async def get_publish_status(post_id: str) -> dict:
    """
    Get publish status for a post across all platforms.
    Returns publish_log rows for the post.
    """
    try:
        # Instantiate dependencies inside tool function
        db = DBManager()
        
        cursor = db.exec(
            "SELECT platform, status, platform_id, platform_url, published_at, error_message "
            "FROM publish_log WHERE post_id = ?",
            (post_id,)
        )
        rows = cursor.fetchall()
        
        if not rows:
            return {"post_id": post_id, "platforms": {}}
        
        platforms = {}
        for row in rows:
            platforms[row[0]] = {
                "status": row[1],
                "platform_id": row[2],
                "platform_url": row[3],
                "published_at": row[4],
                "error_message": row[5]
            }
        
        return {"post_id": post_id, "platforms": platforms}
    except Exception as e:
        logger.error("get_publish_status.error", post_id=post_id, error=str(e))
        return {"error": str(e), "post_id": post_id}


async def update_inventory_status(post_id: str, status: str) -> dict:
    """
    Update status field in inventory.yaml.
    Returns {"updated": True, "post_id": post_id, "status": status}.
    """
    try:
        # Instantiate dependencies inside tool function
        inventory = InventoryManager()
        inventory.update_status(post_id, status)
        return {"updated": True, "post_id": post_id, "status": status}
    except Exception as e:
        logger.error("update_inventory_status.error", post_id=post_id, status=status, error=str(e))
        return {"error": str(e), "post_id": post_id}


async def list_threads() -> list:
    """
    List all post threads with member counts.
    Returns list of thread dicts.
    """
    try:
        # Instantiate dependencies inside tool function
        db = DBManager()
        
        cursor = db.exec(
            "SELECT pt.id, pt.thread_name, pt.description, pt.created_at, COUNT(ptm.post_id) as member_count "
            "FROM post_threads pt "
            "LEFT JOIN post_thread_members ptm ON pt.id = ptm.thread_id "
            "GROUP BY pt.id"
        )
        rows = cursor.fetchall()
        
        threads = []
        for row in rows:
            threads.append({
                "id": row[0],
                "thread_name": row[1],
                "description": row[2],
                "created_at": row[3],
                "member_count": row[4]
            })
        
        return threads
    except Exception as e:
        logger.error("list_threads.error", error=str(e))
        return [{"error": str(e)}]


async def add_to_thread(post_id: str, thread_name: str, sequence: int = None) -> dict:
    """
    Add a post to a thread. Creates thread if it doesn't exist.
    Returns {"added": True, "post_id": post_id, "thread": thread_name}.
    """
    try:
        # Instantiate dependencies inside tool function
        db = DBManager()

        # Check if thread exists
        cursor = db.exec(
            "SELECT id FROM post_threads WHERE thread_name = ?",
            (thread_name,)
        )
        row = cursor.fetchone()

        if row:
            thread_id = row[0]
        else:
            # Create new thread
            cursor = db.exec(
                "INSERT INTO post_threads (thread_name, description) VALUES (?, ?)",
                (thread_name, "")
            )
            db.exec("COMMIT")
            thread_id = cursor.lastrowid

        # Determine sequence
        if sequence is None:
            cursor = db.exec(
                "SELECT MAX(sequence) FROM post_thread_members WHERE thread_id = ?",
                (thread_id,)
            )
            row = cursor.fetchone()
            sequence = (row[0] or 0) + 1

        # Add post to thread
        db.exec(
            "INSERT OR REPLACE INTO post_thread_members (post_id, thread_id, sequence) VALUES (?, ?, ?)",
            (post_id, thread_id, sequence)
        )
        db.exec("COMMIT")

        return {"added": True, "post_id": post_id, "thread": thread_name, "sequence": sequence}
    except Exception as e:
        logger.error("add_to_thread.error", post_id=post_id, thread_name=thread_name, error=str(e))
        return {"error": str(e), "post_id": post_id}


async def get_wordpress_posts(
    status: str = "any",
    per_page: int = 20,
    search: str = None
) -> list[dict]:
    """
    List posts on WordPress blog.
    status: "publish" | "draft" | "any" (default: any)
    per_page: max results (default: 20)
    search: optional search term
    Returns list of {id, title, status, link, date}
    On error: [{"error": str(e)}]
    """
    try:
        wp_handler = _get_wp_handler()
        return await wp_handler.get_posts(status=status, per_page=per_page, search=search)
    except Exception as e:
        logger.error("get_wordpress_posts.error", error=str(e))
        return [{"error": str(e)}]


async def get_wordpress_post(wp_post_id: int) -> dict:
    """
    Fetch full content of a single WordPress post by ID.
    Returns full post dict including rendered content.
    On error: {"error": str(e)}
    """
    try:
        wp_handler = _get_wp_handler()
        return await wp_handler.get_post(wp_post_id)
    except Exception as e:
        logger.error("get_wordpress_post.error", wp_post_id=wp_post_id, error=str(e))
        return {"error": str(e), "wp_post_id": wp_post_id}


async def update_wordpress_post(
    wp_post_id: int,
    title: str = None,
    content: str = None,
    status: str = None,
    tags: list = None,
    categories: list = None,
    date: str = None
) -> dict:
    """
    Update an existing WordPress post.
    Only fields provided are updated — all parameters optional.
    date: ISO 8601 string e.g. "2026-08-09T09:00:00" to reschedule a post.
    Returns {wp_post_id, wp_url, status}
    On error: {"error": str(e)}
    Requires explicit approval — do not call without Robert's confirmation.
    """
    try:
        wp_handler = _get_wp_handler()

        # Build update payload with only provided fields
        fields = {}
        if title is not None:
            fields["title"] = title
        if content is not None:
            fields["content"] = content
        if status is not None:
            fields["status"] = status
        if tags is not None:
            fields["tags"] = tags
        if categories is not None:
            fields["categories"] = categories
        if date is not None:
            fields["date"] = date

        # Use existing update_post method (needs post_id for logging)
        # For WordPress-only updates, we don't have the internal post_id
        # Call the handler's update_post directly with a placeholder
        result = await wp_handler.update_post(
            post_id=f"wp-{wp_post_id}",
            wp_post_id=wp_post_id,
            fields=fields
        )

        return {**result, "status": status or "unchanged"}
    except Exception as e:
        logger.error("update_wordpress_post.error", wp_post_id=wp_post_id, error=str(e))
        return {"error": str(e), "wp_post_id": wp_post_id}


async def get_wordpress_categories() -> list[dict]:
    """
    List all categories on the WordPress blog.
    Returns list of {id, name, slug, count}
    Use before publishing to assign correct category IDs.
    On error: [{"error": str(e)}]
    """
    try:
        wp_handler = _get_wp_handler()
        return await wp_handler.get_categories()
    except Exception as e:
        logger.error("get_wordpress_categories.error", error=str(e))
        return [{"error": str(e)}]


def register_publish_tools(mcp):
    """Register publishing tools with FastMCP server."""
    mcp.tool()(publish_to_wordpress)
    mcp.tool()(publish_to_devto)
    mcp.tool()(update_devto_post)
    mcp.tool()(get_publish_status)
    mcp.tool()(update_inventory_status)
    mcp.tool()(list_threads)
    mcp.tool()(add_to_thread)
    mcp.tool()(get_wordpress_posts)
    mcp.tool()(get_wordpress_post)
    mcp.tool()(update_wordpress_post)
    mcp.tool()(get_wordpress_categories)

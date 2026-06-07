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


async def publish_to_wordpress(post_id: str, publish: bool = False) -> dict:
    """
    Publish approved draft to WordPress.
    Draft must have status: approved. Calls approval gate.
    publish=False creates WP draft. publish=True publishes immediately.
    Returns: {post_id, wp_post_id, wp_url, status}
    On error: {"error": str(e), "post_id": post_id}
    """
    try:
        publisher = _get_publisher()
        return await publisher.publish_wordpress(post_id, publish=publish)
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


def register_publish_tools(mcp):
    """Register publishing tools with FastMCP server."""
    mcp.tool()(publish_to_wordpress)
    mcp.tool()(publish_to_devto)
    mcp.tool()(get_publish_status)
    mcp.tool()(update_inventory_status)
    mcp.tool()(list_threads)
    mcp.tool()(add_to_thread)

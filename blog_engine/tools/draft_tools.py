"""
blog_engine/tools/draft_tools.py

MCP tools for draft management.
"""

from blog_engine.infra.db_manager import DBManager
from blog_engine.infra.logger import get_logger
from blog_engine.core.inventory import InventoryManager
from blog_engine.core.draft_manager import DraftManager

logger = get_logger(__name__)


def _get_draft_manager():
    """Factory function to instantiate DraftManager with DBManager."""
    db = DBManager()
    return DraftManager(db=db)


async def register_post(
    post_id: str,
    title: str,
    category: str,
    notes: str,
    tags: list,
    scheduled_date: str = None
) -> dict:
    """
    Register a new post in the inventory.
    Creates data/inventory/{post_id}.yaml with status: pending.
    Raises if post_id already exists.
    Returns the new post dict.
    scheduled_date: optional ISO 8601 string e.g. "2026-07-19T09:00:00"
    """
    try:
        inventory = InventoryManager()
        return inventory.add_post(
            post_id=post_id,
            title=title,
            category=category,
            notes=notes,
            tags=tags,
            scheduled_date=scheduled_date
        )
    except Exception as e:
        logger.error("register_post.error", post_id=post_id, error=str(e))
        return {"error": str(e), "post_id": post_id}


async def list_inventory(status: str = "pending", thread: str = None) -> list:
    """
    List posts from inventory, optionally filtered by status or thread.
    Returns list of post dicts.
    """
    try:
        # Instantiate dependencies inside tool function
        inventory = InventoryManager()
        db = DBManager()
        
        if thread:
            # Query thread members
            cursor = db.exec(
                "SELECT pt.thread_name, ptm.post_id, ptm.sequence "
                "FROM post_threads pt "
                "JOIN post_thread_members ptm ON pt.id = ptm.thread_id "
                "WHERE pt.thread_name = ?",
                (thread,)
            )
            rows = cursor.fetchall()
            
            if not rows:
                return [{"warning": "thread not found", "thread": thread}]
            
            # Get full post data for each member
            posts = []
            for row in rows:
                post = inventory.get_post(row[1])
                if post:
                    post["sequence"] = row[2]
                    posts.append(post)
            return posts
        else:
            # Filter by status
            return inventory.list_by_status(status)
    except Exception as e:
        logger.error("list_inventory.error", status=status, thread=thread, error=str(e))
        return [{"error": str(e)}]


async def get_draft(post_id: str) -> dict:
    """
    Get a draft by post_id.
    Returns draft dict or {"error": "not found"}.
    """
    try:
        # Instantiate dependencies inside tool function
        draft_manager = _get_draft_manager()
        draft = draft_manager.get_draft(post_id)
        if draft:
            return draft
        return {"error": "not found", "post_id": post_id}
    except Exception as e:
        logger.error("get_draft.error", post_id=post_id, error=str(e))
        return {"error": str(e), "post_id": post_id}


async def create_draft(
    post_id: str,
    title: str,
    content: str,
    tags: list = [],
    categories: list = [],
    tags_source: str = "manual"
) -> dict:
    """
    Create a new draft.
    Returns draft dict.
    """
    try:
        # Instantiate dependencies inside tool function
        draft_manager = _get_draft_manager()
        draft_manager.create_draft(
            post_id=post_id,
            title=title,
            content=content,
            tags=tags,
            categories=categories,
            tags_source=tags_source,
            categories_source="manual",
            generation_source="external"
        )
        return draft_manager.get_draft(post_id)
    except Exception as e:
        logger.error("create_draft.error", post_id=post_id, error=str(e))
        return {"error": str(e), "post_id": post_id}


async def update_draft(post_id: str, content: str, title: str = None, saved_by: str = "human") -> dict:
    """
    Update an existing draft.
    Optionally update title.
    Returns updated draft dict.
    """
    try:
        # Instantiate dependencies inside tool function
        draft_manager = _get_draft_manager()
        draft_manager.update_draft(post_id, content, title=title, saved_by=saved_by)
        return draft_manager.get_draft(post_id)
    except Exception as e:
        logger.error("update_draft.error", post_id=post_id, error=str(e))
        return {"error": str(e), "post_id": post_id}


async def approve_draft(post_id: str, approved_by: str = "human") -> dict:
    """
    Approve a draft for publishing.
    Returns updated draft dict.
    """
    try:
        # Instantiate dependencies inside tool function
        draft_manager = _get_draft_manager()
        draft_manager.approve_draft(post_id, approved_by=approved_by)
        return draft_manager.get_draft(post_id)
    except Exception as e:
        logger.error("approve_draft.error", post_id=post_id, error=str(e))
        return {"error": str(e), "post_id": post_id}


async def delete_draft(post_id: str) -> dict:
    """
    Delete a draft.
    Returns {"deleted": True, "post_id": post_id}.
    """
    try:
        # Instantiate dependencies inside tool function
        draft_manager = _get_draft_manager()
        draft_manager.delete_draft(post_id)
        return {"deleted": True, "post_id": post_id}
    except Exception as e:
        logger.error("delete_draft.error", post_id=post_id, error=str(e))
        return {"error": str(e), "post_id": post_id}


async def revert_revision(post_id: str, revision_number: int) -> dict:
    """
    Revert draft to a specific revision.
    Returns updated draft dict.
    """
    try:
        # Instantiate dependencies inside tool function
        draft_manager = _get_draft_manager()
        draft_manager.revert_revision(post_id, revision_number)
        return draft_manager.get_draft(post_id)
    except Exception as e:
        logger.error("revert_revision.error", post_id=post_id, revision_number=revision_number, error=str(e))
        return {"error": str(e), "post_id": post_id}


async def get_revision_history(post_id: str) -> list:
    """
    Get revision history for a draft.
    Returns list of revision dicts.
    """
    try:
        # Instantiate dependencies inside tool function
        draft_manager = _get_draft_manager()
        return draft_manager.get_revision_history(post_id)
    except Exception as e:
        logger.error("get_revision_history.error", post_id=post_id, error=str(e))
        return [{"error": str(e), "post_id": post_id}]


def register_draft_tools(mcp):
    """Register draft management tools with FastMCP server."""
    mcp.tool()(register_post)
    mcp.tool()(list_inventory)
    mcp.tool()(get_draft)
    mcp.tool()(create_draft)
    mcp.tool()(update_draft)
    mcp.tool()(approve_draft)
    mcp.tool()(delete_draft)
    mcp.tool()(revert_revision)
    mcp.tool()(get_revision_history)

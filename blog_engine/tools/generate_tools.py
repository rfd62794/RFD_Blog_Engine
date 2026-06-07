"""
blog_engine/tools/generate_tools.py

MCP tools for blog post generation.
"""

from blog_engine.infra.db_manager import DBManager
from blog_engine.infra.logger import get_logger
from blog_engine.core.inventory import InventoryManager
from blog_engine.core.generator import PostGenerator
from blog_engine.core.draft_manager import DraftManager

logger = get_logger(__name__)


async def generate_post(post_id: str, model: str = None, override_frame: bool = False) -> dict:
    """
    Generate a blog post draft using the internal model router.
    Uses RFD Content Frame prompt. Saves draft to data/drafts/{post_id}.json.
    Returns: {post_id, title, status, generation_source, revision_count}
    Raises if post not in inventory, draft exists without override, or all models fail.
    """
    try:
        # Instantiate dependencies inside tool function
        db = DBManager()
        inventory = InventoryManager()
        draft_manager = DraftManager()
        generator = PostGenerator(db, inventory, draft_manager)
        
        result = await generator.generate(post_id, model=model, override_frame=override_frame)
        return result
    except Exception as e:
        logger.error("generate_post.error", post_id=post_id, error=str(e))
        return {"error": str(e), "post_id": post_id}


async def get_post_context(post_id: str) -> dict:
    """
    Returns full context for a post: inventory fields + SQLite frame slots.
    Use before generate_post to understand what context exists.
    Returns: {post_id, title, category, notes, tags, frame_slots: {moment, surprise, struggle, lesson, next}}
    """
    try:
        # Instantiate dependencies inside tool function
        db = DBManager()
        inventory = InventoryManager()
        
        # Get inventory context
        inventory_context = inventory.get_context_for_generation(post_id)
        
        # Get frame context from SQLite
        cursor = db.exec(
            "SELECT frame_moment, frame_surprise, frame_struggle, frame_lesson, frame_next "
            "FROM post_context WHERE post_id = ?",
            (post_id,)
        )
        row = cursor.fetchone()
        
        if row:
            frame_slots = {
                "moment": row[0] or "",
                "surprise": row[1] or "",
                "struggle": row[2] or "",
                "lesson": row[3] or "",
                "next": row[4] or ""
            }
        else:
            frame_slots = {
                "moment": "",
                "surprise": "",
                "struggle": "",
                "lesson": "",
                "next": ""
            }
        
        return {
            "post_id": inventory_context["post_id"],
            "title": inventory_context["title"],
            "category": inventory_context["category"],
            "notes": inventory_context["notes"],
            "tags": inventory_context["tags"],
            "frame_slots": frame_slots
        }
    except KeyError as e:
        return {"error": f"Post not found: {post_id}", "post_id": post_id}
    except Exception as e:
        logger.error("get_post_context.error", post_id=post_id, error=str(e))
        return {"error": str(e), "post_id": post_id}


def register_generate_tools(mcp):
    """Register generation tools with FastMCP server."""
    mcp.tool()(generate_post)
    mcp.tool()(get_post_context)

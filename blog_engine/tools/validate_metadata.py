"""
blog_engine/tools/validate_metadata.py

Metadata validator for posts across WordPress and Dev.to.
Checks excerpt, categories, tags, featured image, slug format, schedule, and canonical URLs.
"""

import os
import asyncio
from typing import Optional
from datetime import datetime
import aiohttp

from blog_engine.infra.db_manager import DBManager
from blog_engine.infra.logger import get_logger

logger = get_logger(__name__)

# Credentials from environment
WP_URL = os.getenv("WORDPRESS_URL", "").rstrip("/")
WP_USER = os.getenv("WORDPRESS_USER", "")
WP_APP_PASSWORD = os.getenv("WORDPRESS_APP_PASSWORD", "")
DEVTO_API_KEY = os.getenv("DEVTO_API_KEY", "")


async def _wp_api_get(endpoint: str, params: dict = None) -> dict:
    """Make authenticated GET request to WordPress REST API."""
    import aiohttp
    
    url = f"{WP_URL}/wp-json/wp/v2/{endpoint}"
    auth = aiohttp.BasicAuth(WP_USER, WP_APP_PASSWORD)
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, auth=auth) as resp:
            resp.raise_for_status()
            return await resp.json()


async def _devto_api_get(article_id: str) -> dict:
    """Make authenticated GET request to Dev.to API for an article."""
    import aiohttp
    
    url = f"https://dev.to/api/articles/{article_id}"
    headers = {"api-key": DEVTO_API_KEY}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            resp.raise_for_status()
            return await resp.json()


def _get_post_from_db(post_id: str) -> Optional[dict]:
    """Get post metadata from inventory/database."""
    db = DBManager()
    
    # Check publish_log for platform data
    cursor = db.exec(
        "SELECT platform, platform_id, platform_url FROM publish_log WHERE post_id = ?",
        (post_id,),
    )
    rows = cursor.fetchall()
    
    result = {"post_id": post_id, "platforms": {}}
    for row in rows:
        platform, platform_id, platform_url = row
        result["platforms"][platform] = {
            "id": platform_id,
            "url": platform_url,
        }
    
    return result if result["platforms"] else None


async def validate_post_metadata(post_id: str) -> dict:
    """
    Validate post metadata across WordPress and Dev.to.
    
    Args:
        post_id: Engine post ID (e.g., 'dev-001')
        
    Returns:
        Dict with validation results for each check:
        - excerpt_present: bool
        - excerpt_non_empty: bool
        - has_categories: bool
        - has_minimum_tags: bool (>=3)
        - has_featured_image: bool
        - slug_not_query_fallback: bool (not ?p=ID format)
        - schedule_valid: bool (future date for scheduled)
        - canonical_matches: bool (Dev.to canonical == WP URL)
        - errors: list of error strings
    """
    result = {
        "post_id": post_id,
        "excerpt_present": False,
        "excerpt_non_empty": False,
        "has_categories": False,
        "has_meaningful_category": False,
        "has_minimum_tags": False,
        "has_featured_image": False,
        "slug_not_query_fallback": False,
        "schedule_valid": True,  # Default true unless scheduled with past date
        "canonical_matches": None,  # None if no Dev.to ID, True/False otherwise
        "errors": [],
    }
    
    # Get platform data from DB
    db_post = _get_post_from_db(post_id)
    if not db_post:
        result["errors"].append(f"No publish_log entry found for {post_id}")
        return result
    
    # Check WordPress if published there
    wp_data = None
    if "wordpress" in db_post["platforms"]:
        wp_id = db_post["platforms"]["wordpress"].get("id")
        if wp_id:
            try:
                wp_posts = await _wp_api_get(f"posts/{wp_id}")
                if isinstance(wp_posts, list) and len(wp_posts) > 0:
                    wp_data = wp_posts[0]
                elif isinstance(wp_posts, dict):
                    wp_data = wp_posts
            except Exception as e:
                logger.error("wp_fetch_failed", post_id=post_id, error=str(e))
                result["errors"].append(f"WP fetch failed: {e}")
    
    if wp_data:
        # Check excerpt
        excerpt = wp_data.get("excerpt", {}).get("rendered", "")
        result["excerpt_present"] = bool(excerpt)
        result["excerpt_non_empty"] = bool(excerpt and excerpt.strip())
        
        # Check categories — [1] is Uncategorized (default only, not meaningful)
        categories = wp_data.get("categories", [])
        result["has_categories"] = len(categories) > 0
        result["has_meaningful_category"] = any(c != 1 for c in categories)
        
        # Check tags
        tags = wp_data.get("tags", [])
        result["has_minimum_tags"] = len(tags) >= 3
        
        # Check featured image
        featured_media = wp_data.get("featured_media", 0)
        result["has_featured_image"] = featured_media > 0
        
        # Check slug format
        # For published posts: check link field is pretty permalink.
        # For future/scheduled posts: WordPress serves ?p= links until publish;
        # instead validate that the slug field is non-empty and not numeric-only.
        link = wp_data.get("link", "")
        slug = wp_data.get("slug", "")
        status = wp_data.get("status", "")
        if status == "future":
            result["slug_not_query_fallback"] = bool(slug) and not slug.isdigit()
        else:
            result["slug_not_query_fallback"] = not ("?p=" in link or "?page_id=" in link)
        
        # Check schedule (if post is scheduled for future)
        date_str = wp_data.get("date", "")
        if status == "future" and date_str:
            try:
                post_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                if post_date <= datetime.now(post_date.tzinfo):
                    result["schedule_valid"] = False
                    result["errors"].append("Scheduled post has past date")
            except Exception as e:
                logger.warning("schedule_parse_error", post_id=post_id, error=str(e))
    
    # Check Dev.to canonical URL if applicable
    if "devto" in db_post["platforms"]:
        devto_id = db_post["platforms"]["devto"].get("id")
        if devto_id and wp_data:
            try:
                devto_article = await _devto_api_get(devto_id)
                devto_canonical = devto_article.get("canonical_url", "")
                wp_link = wp_data.get("link", "")
                
                # Normalize URLs for comparison
                result["canonical_matches"] = devto_canonical.rstrip("/") == wp_link.rstrip("/")
                
                if not result["canonical_matches"]:
                    result["errors"].append(
                        f"Canonical mismatch: Dev.to={devto_canonical}, WP={wp_link}"
                    )
            except Exception as e:
                logger.error("devto_fetch_failed", post_id=post_id, error=str(e))
                result["errors"].append(f"Dev.to fetch failed: {e}")
    
    return result


async def audit_all_posts() -> list[dict]:
    """
    Run validator against all posts with publish_log entries.
    Returns list of validation results with failing checks flagged.
    """
    db = DBManager()
    
    # Get all unique post_ids from publish_log
    cursor = db.exec("SELECT DISTINCT post_id FROM publish_log")
    post_ids = [row[0] for row in cursor.fetchall()]
    
    results = []
    for post_id in post_ids:
        try:
            validation = await validate_post_metadata(post_id)
            results.append(validation)
        except Exception as e:
            logger.error("audit_failed", post_id=post_id, error=str(e))
            results.append({
                "post_id": post_id,
                "error": str(e),
                "errors": [f"Audit failed: {e}"],
            })
    
    return results


def check_schedule_collisions(posts_data: list[dict]) -> list[tuple]:
    """
    Check for posts sharing the same scheduled date.
    Returns list of (post_id_1, post_id_2, date) tuples for collisions.
    """
    from collections import defaultdict
    
    date_to_posts = defaultdict(list)
    
    for post in posts_data:
        scheduled_date = post.get("scheduled_date")
        if scheduled_date:
            date_to_posts[scheduled_date].append(post["post_id"])
    
    collisions = []
    for date, post_ids in date_to_posts.items():
        if len(post_ids) > 1:
            # Return all pairwise collisions
            for i in range(len(post_ids)):
                for j in range(i + 1, len(post_ids)):
                    collisions.append((post_ids[i], post_ids[j], date))
    
    return collisions


async def get_permalink_structure() -> dict:
    """
    Verify WordPress permalink structure by checking published posts.
    Returns verdict on whether permalinks are /slug/ or ?p=ID format.
    """
    try:
        # Fetch a sample of published posts
        posts = await _wp_api_get("posts", {"per_page": 5, "status": "publish"})
        
        if not posts:
            return {"verdict": "unknown", "reason": "No published posts found"}
        
        results = []
        for post in posts:
            link = post.get("link", "")
            slug = post.get("slug", "")
            is_pretty = "/" in link and "?p=" not in link and "?page_id=" not in link
            results.append({
                "id": post.get("id"),
                "link": link,
                "slug": slug,
                "is_pretty_permalink": is_pretty,
            })
        
        # If majority have pretty permalinks, assume that's the structure
        pretty_count = sum(1 for r in results if r["is_pretty_permalink"])
        total = len(results)
        
        if pretty_count == total:
            verdict = "/slug/ format (pretty permalinks)"
        elif pretty_count == 0:
            verdict = "?p=ID format (query string permalinks)"
        else:
            verdict = "mixed (investigate manually)"
        
        return {
            "verdict": verdict,
            "pretty_count": pretty_count,
            "total": total,
            "sample": results,
        }
        
    except Exception as e:
        logger.error("permalink_check_failed", error=str(e))
        return {"verdict": "error", "reason": str(e)}


async def fix_devto_canonical(devto_article_id: str, correct_canonical_url: str) -> dict:
    """
    Update Dev.to article's canonical_url to the correct value.
    This is the single external write operation permitted by the directive.
    
    Args:
        devto_article_id: Dev.to article ID (e.g., '3844728')
        correct_canonical_url: The correct canonical URL to set
        
    Returns:
        Dict with before/after values and status.
    """
    import aiohttp
    
    # First, read current article state
    url = f"https://dev.to/api/articles/{devto_article_id}"
    headers = {"api-key": DEVTO_API_KEY}
    
    async with aiohttp.ClientSession() as session:
        # Get current canonical
        async with session.get(url, headers=headers) as resp:
            resp.raise_for_status()
            article = await resp.json()
            before_canonical = article.get("canonical_url", "")
        
        # Update canonical URL via PUT
        update_url = f"https://dev.to/api/articles/{devto_article_id}"
        update_body = {
            "article": {
                "canonical_url": correct_canonical_url
            }
        }
        
        async with session.put(update_url, headers=headers, json=update_body) as resp:
            resp.raise_for_status()
            updated = await resp.json()
            after_canonical = updated.get("canonical_url", "")
        
        return {
            "article_id": devto_article_id,
            "before": before_canonical,
            "after": after_canonical,
            "expected": correct_canonical_url,
            "success": after_canonical.rstrip("/") == correct_canonical_url.rstrip("/"),
        }


def register_validate_metadata_tools(mcp):
    """Register metadata validation tools with FastMCP server."""
    mcp.tool()(validate_post_metadata)
    mcp.tool()(audit_all_posts)
    mcp.tool()(get_permalink_structure)

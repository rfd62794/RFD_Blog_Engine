"""
blog_engine/core/publisher.py

Publish orchestration for rfd-blog-engine.
Handles approval gate, WordPress publish, Dev.to syndication, and inventory updates.
"""

from datetime import datetime, timezone
from pathlib import Path
import json
import os

from blog_engine.infra.db_manager import DBManager
from blog_engine.infra.logger import get_logger
from blog_engine.core.draft_manager import DraftManager
from blog_engine.core.inventory import InventoryManager
from blog_engine.core import content_guard
from blog_engine.api.wordpress import WordPressHandler, ROBERT_ONLY_PUBLISH_MESSAGE
from blog_engine.api.devto import DevToHandler


class Publisher:
    def __init__(
        self,
        db: DBManager,
        draft_manager: DraftManager,
        inventory: InventoryManager,
        wp_handler: WordPressHandler,
        devto_handler: DevToHandler
    ):
        self.db = db
        self.drafts = draft_manager
        self.inventory = inventory
        self.wp = wp_handler
        self.devto = devto_handler
        self.logger = get_logger(__name__)

    async def publish_wordpress(
        self,
        post_id: str,
        publish: bool = False,
        scheduled_date: str = None
    ) -> dict:
        """
        Push an approved draft to WordPress for Robert's review.

        The engine never publishes: the WordPress post is created with
        status "pending" and Robert publishes (or schedules) it in WordPress.
        publish=True or a scheduled_date are refused — those belong to Robert.

        1. Refuse publish=True / scheduled_date — ValueError, no WP call
        2. Load draft — raise ValueError if not found
        3. Check approval — raise ValueError if status != "approved"
        4. Content guard — raise ValueError listing every problem found
        5. Call WordPressHandler.create_post with status="pending"
        6. Update draft JSON with wp_post_id and wp_url
        7. Return {post_id, wp_post_id, wp_url, status: "pending", note}
        """
        self.logger.info("publish_wordpress.start", post_id=post_id, publish=publish, scheduled_date=scheduled_date)

        # Publishing and scheduling are Robert's — refuse before any WP call.
        if publish or scheduled_date is not None:
            raise ValueError(ROBERT_ONLY_PUBLISH_MESSAGE)

        # Load draft
        draft = self.drafts.get_draft(post_id)
        if draft is None:
            raise ValueError(f"Draft not found for post_id: {post_id}")

        # Check approval
        self._check_approved(draft)

        # Content guard — placeholders and unfinished markers never leave the engine
        problems = content_guard.check(draft)
        if problems:
            raise ValueError(
                f"draft {post_id} failed content checks: " + "; ".join(problems)
            )

        # Only include tags/categories if they are integer IDs (WordPress expects IDs, not strings)
        tags = draft.get("tags", [])
        if tags and all(isinstance(t, int) for t in tags):
            tags_to_send = tags
        else:
            tags_to_send = []

        categories = draft.get("categories", [])
        if categories and all(isinstance(c, int) for c in categories):
            categories_to_send = categories
        else:
            categories_to_send = []

        wp_result = await self.wp.create_post(
            post_id=post_id,
            title=draft["title"],
            content=draft["content"],
            excerpt=draft.get("excerpt", ""),
            tags=tags_to_send,
            categories=categories_to_send,
            status="pending"
        )
        
        # Update draft JSON with WordPress fields
        self._update_draft_publish_fields(
            post_id=post_id,
            wp_post_id=wp_result["wp_post_id"],
            wp_url=wp_result["wp_url"]
        )
        
        # Inventory mirrors the draft's status: still "approved" — nothing is
        # "published" until Robert publishes it in WordPress.
        self.inventory.update_status(post_id, "approved")

        # Backfill wp_post_id into inventory YAML — non-fatal if it fails (post is already in WP)
        try:
            self._backfill_inventory_wp_post_id(post_id, wp_result["wp_post_id"])
        except Exception as e:
            self.logger.error(
                "publish_wordpress.inventory_backfill_failed",
                post_id=post_id,
                wp_post_id=wp_result["wp_post_id"],
                error=str(e)
            )

        self.logger.info(
            "publish_wordpress.success",
            post_id=post_id,
            wp_post_id=wp_result["wp_post_id"],
            wp_url=wp_result["wp_url"]
        )
        
        return {
            "post_id": post_id,
            "wp_post_id": wp_result["wp_post_id"],
            "wp_url": wp_result["wp_url"],
            "status": "pending",
            "note": "Robert publishes in WordPress"
        }

    async def publish_devto(
        self,
        post_id: str,
        published: bool = False
    ) -> dict:
        """
        Full Dev.to publish flow:
        1. Load draft — raise ValueError if not found
        2. Check approval — raise ValueError if status != "approved"
        3. Check wp_url exists on draft — raise ValueError if None
           (WordPress must be published first)
        4. Verify the WordPress post is actually live — GET it by wp_post_id
           and refuse unless its status is "publish"
        5. Call DevToHandler.create_article with canonical_url=draft.wp_url
        6. Update draft JSON with devto_id and devto_url
        7. Return {post_id, devto_id, devto_url, canonical_url, status}
        """
        api_key = os.getenv("DEVTO_API_KEY", "")
        if not api_key:
            return {"error": "DEVTO_API_KEY not configured", "post_id": post_id}

        self.logger.info("publish_devto.start", post_id=post_id, published=published)
        
        # Load draft
        draft = self.drafts.get_draft(post_id)
        if draft is None:
            raise ValueError(f"Draft not found for post_id: {post_id}")
        
        # Check approval
        self._check_approved(draft)
        
        # Check wp_url exists
        if not draft.get("wp_url"):
            raise ValueError(
                "WordPress must be published before Dev.to. "
                "Call publish_to_wordpress first."
            )

        # Dev.to only follows a post that is actually live on WordPress —
        # verify by fetching the post and checking its status is "publish".
        wp_post_id = draft.get("wp_post_id")
        if not wp_post_id:
            raise ValueError(
                "Cannot verify WordPress status for this post: no wp_post_id "
                "on draft. Push to WordPress first."
            )
        wp_post = await self.wp.get_post(int(wp_post_id))
        wp_status = wp_post.get("status") if isinstance(wp_post, dict) else None
        if wp_status != "publish":
            raise ValueError(
                f"Dev.to syndication requires a live WordPress post; "
                f"wp_post_id {wp_post_id} has status '{wp_status}'. "
                f"Robert publishes in WordPress."
            )

        # Call Dev.to API — update if article already exists, create otherwise
        existing_devto_id = draft.get("devto_id")
        if existing_devto_id:
            devto_result = await self.devto.update_article(
                post_id=post_id,
                devto_id=existing_devto_id,
                fields={
                    "title": draft["title"],
                    "body_markdown": draft["content"],
                    "canonical_url": draft["wp_url"],
                    "tags": draft.get("tags", []),
                    "published": published,
                }
            )
        else:
            devto_result = await self.devto.create_article(
                post_id=post_id,
                title=draft["title"],
                body_markdown=draft["content"],
                canonical_url=draft["wp_url"],
                tags=draft.get("tags", []),
                published=published
            )
        
        # Propagate API error before touching keys
        if "error" in devto_result:
            self.logger.error("publish_devto.api_error", post_id=post_id, error=devto_result["error"])
            return devto_result

        # Update draft JSON with Dev.to fields
        self._update_draft_publish_fields(
            post_id=post_id,
            devto_id=devto_result["devto_id"],
            devto_url=devto_result["devto_url"]
        )
        
        self.logger.info(
            "publish_devto.success",
            post_id=post_id,
            devto_id=devto_result["devto_id"],
            devto_url=devto_result["devto_url"],
            canonical_url=draft["wp_url"]
        )
        
        return {
            "post_id": post_id,
            "devto_id": devto_result["devto_id"],
            "devto_url": devto_result["devto_url"],
            "canonical_url": draft["wp_url"],
            "status": "published"
        }

    def _check_approved(self, draft: dict) -> None:
        """
        Raises ValueError if draft status is not "approved".
        Message: "Draft {post_id} must be approved before publishing. Current status: {status}"
        """
        if draft.get("status") != "approved":
            raise ValueError(
                f"Draft {draft['post_id']} must be approved before publishing. "
                f"Current status: {draft.get('status')}"
            )

    def _update_draft_publish_fields(
        self,
        post_id: str,
        wp_post_id: int = None,
        wp_url: str = None,
        devto_id: int = None,
        devto_url: str = None
    ) -> None:
        """
        Updates draft JSON with publish result fields.
        Sets published_at timestamp if both wp_url and devto_url are now set.
        Uses atomic write pattern (inherited from DraftManager pattern).
        """
        draft = self.drafts.get_draft(post_id)
        if draft is None:
            raise ValueError(f"Draft not found for post_id: {post_id}")
        
        # Update fields
        if wp_post_id is not None:
            draft["wp_post_id"] = wp_post_id
        if wp_url is not None:
            draft["wp_url"] = wp_url
        if devto_id is not None:
            draft["devto_id"] = devto_id
        if devto_url is not None:
            draft["devto_url"] = devto_url
        
        # Set published_at if both URLs are now present
        if draft.get("wp_url") and draft.get("devto_url") and not draft.get("published_at"):
            draft["published_at"] = datetime.now(timezone.utc).isoformat()
        
        draft["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Atomic write
        draft_path = self.drafts.drafts_dir / f"{post_id}.json"
        self._atomic_write(draft_path, draft)
        
        self.logger.debug("draft_publish_fields_updated", post_id=post_id)

    def _backfill_inventory_wp_post_id(self, post_id: str, wp_post_id: int) -> None:
        """
        Write wp_post_id into the inventory YAML for post_id.
        Atomic write via tmp file. Called after successful WordPress publish.
        Non-fatal caller — any exception is caught and logged by publish_wordpress.
        """
        import yaml
        path = self.inventory.inventory_dir / f"{post_id}.yaml"
        if not path.exists():
            return
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        data["wp_post_id"] = wp_post_id
        tmp_path = path.with_suffix(".yaml.tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
        tmp_path.replace(path)
        self.logger.info("inventory.wp_post_id_backfilled", post_id=post_id, wp_post_id=wp_post_id)

    def _atomic_write(self, path: Path, data: dict) -> None:
        """
        Atomic write pattern: write to .tmp, then rename.
        """
        tmp_path = path.with_suffix(".json.tmp")
        
        with open(tmp_path, "w") as f:
            json.dump(data, f, indent=2)
        
        # Atomic rename
        if os.name == "nt":  # Windows
            if path.exists():
                path.unlink()
        tmp_path.rename(path)

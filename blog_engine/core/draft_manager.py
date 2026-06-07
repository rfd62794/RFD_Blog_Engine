"""
blog_engine/core/draft_manager.py

Draft Manager for rfd-blog-engine.
Handles JSON draft CRUD operations and SQLite context storage.
"""

from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
import json
import os

from blog_engine.infra.db_manager import DBManager
from blog_engine.infra.logger import get_logger

# Resolve drafts path relative to project root (this file's parent parent parent)
DRAFTS_DIR = Path(__file__).parent.parent.parent / "data" / "drafts"
VALID_STATUSES = {"draft", "approved", "published"}
VALID_TAG_SOURCES = {"auto", "manual", "per_post"}
VALID_GENERATION_SOURCES = {"internal", "external"}


class DraftManager:
    def __init__(self, db: DBManager, drafts_dir: Path = None):
        self.db = db
        self.logger = get_logger(__name__)
        self.drafts_dir = drafts_dir or DRAFTS_DIR
        self.drafts_dir.mkdir(parents=True, exist_ok=True)

    # --- Draft CRUD ---

    def create_draft(
        self,
        post_id: str,
        title: str,
        content: str,
        tags: list[str] = None,
        categories: list[str] = None,
        tags_source: str = "manual",
        categories_source: str = "manual",
        generation_source: str = "external"
    ) -> dict:
        """
        Create a new draft JSON file.
        
        Raises ValueError if draft already exists for post_id.
        """
        if tags is None:
            tags = []
        if categories is None:
            categories = []
        
        # Validate enums
        if tags_source not in VALID_TAG_SOURCES:
            raise ValueError(f"Invalid tags_source: {tags_source}. Must be one of {VALID_TAG_SOURCES}")
        if categories_source not in VALID_TAG_SOURCES:
            raise ValueError(f"Invalid categories_source: {categories_source}. Must be one of {VALID_TAG_SOURCES}")
        if generation_source not in VALID_GENERATION_SOURCES:
            raise ValueError(f"Invalid generation_source: {generation_source}. Must be one of {VALID_GENERATION_SOURCES}")
        
        # Check for existing draft
        draft_path = self.drafts_dir / f"{post_id}.json"
        if draft_path.exists():
            raise ValueError(f"Draft already exists for post_id: {post_id}")
        
        now = datetime.now(timezone.utc).isoformat()
        
        draft_data = {
            "post_id": post_id,
            "title": title,
            "status": "draft",
            "content": content,
            "excerpt": "",
            "tags": tags,
            "categories": categories,
            "tags_source": tags_source,
            "categories_source": categories_source,
            "created_at": now,
            "updated_at": now,
            "approved_at": None,
            "approved_by": None,
            "wp_post_id": None,
            "wp_url": None,
            "devto_id": None,
            "devto_url": None,
            "published_at": None,
            "revision_count": 0,
            "generation_source": generation_source
        }
        
        # Atomic write
        self._atomic_write(draft_path, draft_data)
        
        self.logger.info("draft_created", post_id=post_id, title=title)
        return draft_data

    def get_draft(self, post_id: str) -> Optional[dict]:
        """
        Get draft JSON for a post_id.
        Returns None if draft doesn't exist.
        """
        draft_path = self.drafts_dir / f"{post_id}.json"
        if not draft_path.exists():
            return None
        
        with open(draft_path, "r") as f:
            return json.load(f)

    def update_draft(
        self,
        post_id: str,
        content: str,
        title: str = None,
        saved_by: str = "human"
    ) -> dict:
        """
        Update draft content and optionally title.
        Saves revision first, then writes new content.
        """
        draft = self.get_draft(post_id)
        if draft is None:
            raise ValueError(f"Draft not found for post_id: {post_id}")

        # Save current content as revision first
        self.save_revision(post_id, draft["content"], saved_by)

        # Update draft
        draft["content"] = content
        if title is not None:
            draft["title"] = title
        draft["updated_at"] = datetime.now(timezone.utc).isoformat()
        draft["revision_count"] += 1

        draft_path = self.drafts_dir / f"{post_id}.json"
        self._atomic_write(draft_path, draft)

        self.logger.info("draft_updated", post_id=post_id, saved_by=saved_by, revision_count=draft["revision_count"])
        return draft

    def approve_draft(
        self,
        post_id: str,
        approved_by: str = "human"
    ) -> dict:
        """
        Approve a draft for publishing.
        Raises ValueError if draft status is not "draft".
        """
        draft = self.get_draft(post_id)
        if draft is None:
            raise ValueError(f"Draft not found for post_id: {post_id}")
        
        if draft["status"] != "draft":
            raise ValueError(f"Cannot approve draft with status: {draft['status']}")
        
        draft["status"] = "approved"
        draft["approved_at"] = datetime.now(timezone.utc).isoformat()
        draft["approved_by"] = approved_by
        draft["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        draft_path = self.drafts_dir / f"{post_id}.json"
        self._atomic_write(draft_path, draft)
        
        self.logger.info("draft_approved", post_id=post_id, approved_by=approved_by)
        return draft

    def delete_draft(self, post_id: str) -> bool:
        """
        Delete draft JSON and all associated SQLite records.
        Does NOT touch inventory.yaml.
        """
        draft_path = self.drafts_dir / f"{post_id}.json"
        
        # Delete JSON file
        if draft_path.exists():
            draft_path.unlink()
        
        # Delete SQLite records
        self.db.exec(
            "DELETE FROM draft_revisions WHERE post_id = ?",
            (post_id,),
            commit=True
        )
        self.db.exec(
            "DELETE FROM post_context WHERE post_id = ?",
            (post_id,),
            commit=True
        )
        
        self.logger.info("draft_deleted", post_id=post_id)
        return True

    # --- Revision history ---

    def save_revision(
        self,
        post_id: str,
        content: str,
        saved_by: str = "human"
    ) -> int:
        """
        Save a revision of draft content.
        Returns the revision_number.
        """
        # Get next revision number
        cursor = self.db.exec(
            "SELECT COALESCE(MAX(revision_number), 0) FROM draft_revisions WHERE post_id = ?",
            (post_id,)
        )
        next_rev = cursor.fetchone()[0] + 1
        
        self.db.exec(
            """
            INSERT INTO draft_revisions (post_id, revision_number, content, saved_by)
            VALUES (?, ?, ?, ?)
            """,
            (post_id, next_rev, content, saved_by),
            commit=True
        )
        
        self.logger.debug("revision_saved", post_id=post_id, revision_number=next_rev, saved_by=saved_by)
        return next_rev

    def get_revision_history(self, post_id: str) -> list[dict]:
        """
        Get all revisions for a post, ordered by revision_number ascending.
        """
        cursor = self.db.exec(
            """
            SELECT revision_number, content, saved_at, saved_by
            FROM draft_revisions
            WHERE post_id = ?
            ORDER BY revision_number ASC
            """,
            (post_id,)
        )
        
        revisions = []
        for row in cursor.fetchall():
            revisions.append({
                "revision_number": row[0],
                "content": row[1],
                "saved_at": row[2],
                "saved_by": row[3]
            })
        
        return revisions

    def revert_revision(
        self,
        post_id: str,
        revision_number: int
    ) -> dict:
        """
        Revert draft to a specific revision.
        Saves current content as a new revision first (non-destructive).
        """
        draft = self.get_draft(post_id)
        if draft is None:
            raise ValueError(f"Draft not found for post_id: {post_id}")
        
        # Get target revision
        cursor = self.db.exec(
            """
            SELECT content FROM draft_revisions
            WHERE post_id = ? AND revision_number = ?
            """,
            (post_id, revision_number)
        )
        result = cursor.fetchone()
        
        if result is None:
            raise ValueError(f"Revision {revision_number} not found for post_id: {post_id}")
        
        # Save current content as new revision first
        self.save_revision(post_id, draft["content"], "revert")
        
        # Update draft with reverted content
        draft["content"] = result[0]
        draft["updated_at"] = datetime.now(timezone.utc).isoformat()
        draft["revision_count"] += 1
        
        draft_path = self.drafts_dir / f"{post_id}.json"
        self._atomic_write(draft_path, draft)
        
        self.logger.info("revision_reverted", post_id=post_id, to_revision=revision_number)
        return draft

    # --- Context (frame slots) ---

    def save_context(
        self,
        post_id: str,
        raw_extraction: str = None,
        frame_moment: str = None,
        frame_surprise: str = None,
        frame_struggle: str = None,
        frame_lesson: str = None,
        frame_next: str = None,
        related_posts: list[str] = None
    ) -> None:
        """
        Save post context (RFD Content Frame slots).
        """
        if related_posts is None:
            related_posts = []
        
        related_posts_json = json.dumps(related_posts)
        
        self.db.exec(
            """
            INSERT INTO post_context 
            (post_id, raw_extraction, frame_moment, frame_surprise, frame_struggle, frame_lesson, frame_next, related_posts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(post_id) DO UPDATE SET
                raw_extraction = excluded.raw_extraction,
                frame_moment = excluded.frame_moment,
                frame_surprise = excluded.frame_surprise,
                frame_struggle = excluded.frame_struggle,
                frame_lesson = excluded.frame_lesson,
                frame_next = excluded.frame_next,
                related_posts = excluded.related_posts,
                updated_at = CURRENT_TIMESTAMP
            """,
            (post_id, raw_extraction, frame_moment, frame_surprise, frame_struggle, frame_lesson, frame_next, related_posts_json),
            commit=True
        )
        
        self.logger.debug("context_saved", post_id=post_id)

    def get_context(self, post_id: str) -> Optional[dict]:
        """
        Get post context for a post_id.
        Returns None if no context exists.
        """
        cursor = self.db.exec(
            """
            SELECT raw_extraction, frame_moment, frame_surprise, frame_struggle, 
                   frame_lesson, frame_next, related_posts, updated_at
            FROM post_context
            WHERE post_id = ?
            """,
            (post_id,)
        )
        
        result = cursor.fetchone()
        if result is None:
            return None
        
        related_posts = json.loads(result[6]) if result[6] else []
        
        return {
            "post_id": post_id,
            "raw_extraction": result[0],
            "frame_moment": result[1],
            "frame_surprise": result[2],
            "frame_struggle": result[3],
            "frame_lesson": result[4],
            "frame_next": result[5],
            "related_posts": related_posts,
            "updated_at": result[7]
        }

    # --- Private helpers ---

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

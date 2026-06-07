"""
blog_engine/core/inventory.py

Per-post YAML inventory manager.
Scans data/inventory/ directory — one YAML file per post.
"""

from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
import yaml

from blog_engine.infra.logger import get_logger

INVENTORY_DIR = Path(__file__).parent.parent.parent / "data" / "inventory"
VALID_STATUSES = {"pending", "drafted", "approved", "published"}


class InventoryManager:
    def __init__(self, inventory_dir: Path = INVENTORY_DIR):
        self.inventory_dir = inventory_dir
        self.inventory_dir.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger(__name__)

    def load(self) -> list[dict]:
        """Load all posts by scanning inventory_dir/*.yaml. Returns list of post dicts."""
        posts = []
        for path in sorted(self.inventory_dir.glob("*.yaml")):
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data and "post_id" in data:
                posts.append(data)
        return posts

    def get_post(self, post_id: str) -> Optional[dict]:
        """Return single post by post_id. Returns None if not found."""
        path = self.inventory_dir / f"{post_id}.yaml"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def list_by_status(self, status: str) -> list[dict]:
        """Return posts filtered by status. Raises ValueError on invalid status."""
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}. Must be one of {VALID_STATUSES}")
        return [p for p in self.load() if p.get("status") == status]

    def update_status(self, post_id: str, status: str) -> None:
        """
        Update status field for a post.
        Atomic write to individual YAML file.
        Raises ValueError if post_id not found or status invalid.
        """
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}. Must be one of {VALID_STATUSES}")

        path = self.inventory_dir / f"{post_id}.yaml"
        if not path.exists():
            raise ValueError(f"Post not found: {post_id}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        data["status"] = status

        tmp_path = path.with_suffix(".yaml.tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
        tmp_path.replace(path)

        self.logger.info("inventory.status_updated", post_id=post_id, status=status)

    def add_post(
        self,
        post_id: str,
        title: str,
        category: str,
        notes: str,
        tags: list,
        scheduled_date: str = None
    ) -> dict:
        """
        Create a new per-post YAML file.
        Raises ValueError if post_id already exists.
        Returns the new post dict.
        """
        path = self.inventory_dir / f"{post_id}.yaml"
        if path.exists():
            raise ValueError(f"Post already exists: {post_id}")

        data = {
            "post_id": post_id,
            "title": title,
            "status": "pending",
            "category": category,
            "notes": notes,
            "tags": tags,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if scheduled_date is not None:
            data["scheduled_date"] = scheduled_date

        tmp_path = path.with_suffix(".yaml.tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
        tmp_path.replace(path)

        self.logger.info("inventory.post_added", post_id=post_id, title=title)
        return data

    def get_context_for_generation(self, post_id: str) -> dict:
        """
        Returns dict with all fields needed for prompt construction.
        Raises KeyError if post_id not found.
        """
        post = self.get_post(post_id)
        if not post:
            raise KeyError(f"Post not found: {post_id}")

        return {
            "post_id": post["post_id"],
            "title": post.get("title", ""),
            "category": post.get("category", ""),
            "notes": post.get("notes", ""),
            "tags": post.get("tags", []),
            "status": post.get("status", "pending"),
            "scheduled_date": post.get("scheduled_date"),
        }

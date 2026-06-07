"""
blog_engine/core/inventory.py

YAML inventory reader and status writer.
"""

from pathlib import Path
from typing import Optional
import yaml

from blog_engine.infra.logger import get_logger

INVENTORY_PATH = Path("data/inventory.yaml")
VALID_STATUSES = {"pending", "drafted", "approved", "published"}


class InventoryManager:
    def __init__(self, inventory_path: Path = INVENTORY_PATH):
        self.inventory_path = inventory_path
        self.logger = get_logger(__name__)

    def load(self) -> list[dict]:
        """Load all posts from inventory.yaml. Returns list of post dicts."""
        if not self.inventory_path.exists():
            raise FileNotFoundError(f"Inventory file not found: {self.inventory_path}")
        
        with open(self.inventory_path, "r") as f:
            data = yaml.safe_load(f)
        
        return data.get("posts", [])

    def get_post(self, post_id: str) -> Optional[dict]:
        """Return single post by post_id. Returns None if not found."""
        posts = self.load()
        for post in posts:
            if post.get("post_id") == post_id:
                return post
        return None

    def list_by_status(self, status: str) -> list[dict]:
        """Return posts filtered by status. Raises ValueError on invalid status."""
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}. Must be one of {VALID_STATUSES}")
        
        posts = self.load()
        return [p for p in posts if p.get("status") == status]

    def update_status(self, post_id: str, status: str) -> None:
        """
        Update status field for a post in inventory.yaml.
        Atomic write: write to .tmp, rename to .yaml.
        Raises ValueError if post_id not found.
        Raises ValueError if status not in VALID_STATUSES.
        """
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}. Must be one of {VALID_STATUSES}")
        
        data = self.load()
        posts = data.get("posts", [])
        
        post_found = False
        for post in posts:
            if post.get("post_id") == post_id:
                post["status"] = status
                post_found = True
                break
        
        if not post_found:
            raise ValueError(f"Post not found: {post_id}")
        
        # Atomic write
        tmp_path = self.inventory_path.with_suffix(".yaml.tmp")
        with open(tmp_path, "w") as f:
            yaml.safe_dump(data, f, sort_keys=False)
        
        tmp_path.replace(self.inventory_path)
        
        self.logger.info("inventory.status_updated", post_id=post_id, status=status)

    def get_context_for_generation(self, post_id: str) -> dict:
        """
        Returns dict with all fields needed for prompt construction:
        {post_id, title, category, notes, tags, status}
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
            "status": post.get("status", "pending")
        }

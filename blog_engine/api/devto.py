"""
blog_engine/api/devto.py

Dev.to REST API handler for rfd-blog-engine.
"""

from blog_engine.infra.base_api_handler import BaseAPIHandler, BlogEngineHTTPError
from blog_engine.infra.db_manager import DBManager
from blog_engine.infra.logger import get_logger


class DevToHandler(BaseAPIHandler):
    CACHE_PREFIX = "devto"
    
    def __init__(self, db: DBManager, api_key: str):
        super().__init__()
        self.db = db
        self.api_key = api_key
        self.logger = get_logger(__name__)
        self.base_url = "https://dev.to/api"
    
    async def create_article(
        self,
        post_id: str,
        title: str,
        body_markdown: str,
        canonical_url: str,
        tags: list[str] = None,
        published: bool = False
    ) -> dict:
        """
        Create a Dev.to article.
        
        Returns: {"devto_id": int, "devto_url": str, "published": bool}
        Idempotency: checks publish_log first.
        canonical_url is required — raises ValueError if None or empty.
        """
        if tags is None:
            tags = []
        
        # Validate canonical_url
        if not canonical_url:
            raise ValueError("canonical_url is required and cannot be None or empty")
        
        # Truncate tags to max 4
        if len(tags) > 4:
            self.logger.warning(
                "devto_tags_truncated",
                post_id=post_id,
                original_count=len(tags),
                truncated_to=4
            )
            tags = tags[:4]
        
        # Check idempotency first
        existing = self._check_idempotency(post_id, "devto")
        if existing:
            return {
                "devto_id": int(existing["platform_id"]),
                "devto_url": existing["platform_url"],
                "published": published
            }
        
        # Prepare request
        url = f"{self.base_url}/articles"
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "article": {
                "title": title,
                "body_markdown": body_markdown,
                "published": published,
                "canonical_url": canonical_url,
                "tags": tags
            }
        }
        
        try:
            response = await self._make_request(
                method="POST",
                url=url,
                headers=headers,
                json=payload
            )
            
            data = response.json()
            devto_id = data["id"]
            devto_url = data["url"]
            
            # Write success to publish_log
            self._write_publish_log(
                post_id=post_id,
                platform="devto",
                status="success",
                platform_id=str(devto_id),
                platform_url=devto_url
            )
            
            self.logger.info("devto_article_created", post_id=post_id, devto_id=devto_id)
            
            return {
                "devto_id": devto_id,
                "devto_url": devto_url,
                "published": published
            }
        
        except BlogEngineHTTPError as e:
            # Write failure to publish_log
            self._write_publish_log(
                post_id=post_id,
                platform="devto",
                status="failed",
                error_message=e.message
            )
            raise
    
    async def update_article(
        self,
        post_id: str,
        devto_id: int,
        fields: dict
    ) -> dict:
        """
        Update an existing Dev.to article.
        
        Returns: {"devto_id": int, "devto_url": str}
        """
        url = f"{self.base_url}/articles/{devto_id}"
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        try:
            response = await self._make_request(
                method="PUT",
                url=url,
                headers=headers,
                json={"article": fields}
            )
            
            data = response.json()
            devto_url = data["url"]
            
            self.logger.info("devto_article_updated", post_id=post_id, devto_id=devto_id)
            
            return {
                "devto_id": devto_id,
                "devto_url": devto_url
            }
        
        except BlogEngineHTTPError as e:
            self.logger.error("devto_article_update_failed", post_id=post_id, devto_id=devto_id, error=e.message)
            raise
    
    def _check_idempotency(self, post_id: str, platform: str) -> dict | None:
        """
        Query publish_log for existing success record.
        Returns {"platform_id": str, "platform_url": str} if found, else None.
        """
        row = self.db.exec(
            "SELECT platform_id, platform_url FROM publish_log "
            "WHERE post_id = ? AND platform = ? AND status = 'success'",
            (post_id, platform)
        ).fetchone()
        
        if row:
            self.logger.info(
                "idempotency.hit",
                post_id=post_id,
                platform=platform,
                existing_url=row[1]
            )
            return {"platform_id": row[0], "platform_url": row[1]}
        
        return None
    
    def _write_publish_log(
        self,
        post_id: str,
        platform: str,
        status: str,
        platform_id: str = None,
        platform_url: str = None,
        error_message: str = None
    ) -> None:
        """
        Write result to publish_log table.
        ON CONFLICT IGNORE handles duplicate success entries at DB level.
        """
        self.db.exec(
            """
            INSERT INTO publish_log (post_id, platform, status, platform_id, platform_url, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(post_id, platform, status) DO NOTHING
            """,
            (post_id, platform, status, platform_id, platform_url, error_message),
            commit=True
        )

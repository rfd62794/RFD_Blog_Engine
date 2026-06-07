"""
blog_engine/api/wordpress.py

WordPress REST API handler for rfd-blog-engine.
"""

from blog_engine.infra.base_api_handler import BaseAPIHandler, BlogEngineHTTPError
from blog_engine.infra.db_manager import DBManager
from blog_engine.infra.logger import get_logger


class WordPressHandler(BaseAPIHandler):
    CACHE_PREFIX = "wordpress"
    
    def __init__(self, db: DBManager, base_url: str, user: str, app_password: str):
        super().__init__()
        self.db = db
        self.base_url = base_url.rstrip("/")
        self.auth = (user, app_password)
        self.logger = get_logger(__name__)
    
    async def create_post(
        self,
        post_id: str,
        title: str,
        content: str,
        excerpt: str = "",
        tags: list[str] = None,
        categories: list[str] = None,
        status: str = "draft",
        scheduled_date: str = None
    ) -> dict:
        """
        Create a WordPress post.

        Returns: {"wp_post_id": int, "wp_url": str, "status": str}
        Idempotency: checks publish_log first. If success record exists,
        returns existing URL without calling API.
        scheduled_date: ISO 8601 format "2026-06-14T09:00:00". When provided,
        status is forced to "future" regardless of status parameter.
        """
        if tags is None:
            tags = []
        if categories is None:
            categories = []

        # Validate status (unless scheduled_date is provided)
        if scheduled_date is None:
            valid_statuses = {"draft", "publish"}
            if status not in valid_statuses:
                raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")
        else:
            # scheduled_date overrides status to "future"
            status = "future"

        # Check idempotency first
        existing = self._check_idempotency(post_id, "wordpress")
        if existing:
            return {
                "wp_post_id": int(existing["platform_id"]),
                "wp_url": existing["platform_url"],
                "status": status
            }

        # Prepare request
        url = f"{self.base_url}/wp-json/wp/v2/posts"
        payload = {
            "title": title,
            "content": content,
            "excerpt": excerpt,
            "status": status,
            "tags": tags,
            "categories": categories
        }

        # Add date field if scheduled_date provided
        if scheduled_date is not None:
            payload["date"] = scheduled_date
        
        try:
            response = await self._make_request(
                method="POST",
                url=url,
                auth=self.auth,
                json=payload
            )
            
            data = response.json()
            wp_post_id = data["id"]
            wp_url = data["link"]
            
            # Write success to publish_log
            self._write_publish_log(
                post_id=post_id,
                platform="wordpress",
                status="success",
                platform_id=str(wp_post_id),
                platform_url=wp_url
            )
            
            self.logger.info("wp_post_created", post_id=post_id, wp_post_id=wp_post_id)
            
            return {
                "wp_post_id": wp_post_id,
                "wp_url": wp_url,
                "status": status
            }
        
        except BlogEngineHTTPError as e:
            # Write failure to publish_log
            self._write_publish_log(
                post_id=post_id,
                platform="wordpress",
                status="failed",
                error_message=e.message
            )
            raise
    
    async def update_post(
        self,
        post_id: str,
        wp_post_id: int,
        fields: dict
    ) -> dict:
        """
        Update an existing WordPress post by wp_post_id.
        
        Returns: {"wp_post_id": int, "wp_url": str}
        """
        url = f"{self.base_url}/wp-json/wp/v2/posts/{wp_post_id}"
        
        try:
            response = await self._make_request(
                method="POST",
                url=url,
                auth=self.auth,
                json=fields
            )
            
            data = response.json()
            wp_url = data["link"]
            
            self.logger.info("wp_post_updated", post_id=post_id, wp_post_id=wp_post_id)
            
            return {
                "wp_post_id": wp_post_id,
                "wp_url": wp_url
            }
        
        except BlogEngineHTTPError as e:
            self.logger.error("wp_post_update_failed", post_id=post_id, wp_post_id=wp_post_id, error=e.message)
            raise
    
    async def get_post(self, wp_post_id: int) -> dict:
        """
        Fetch a WordPress post by ID.
        Returns raw WP API response dict.
        """
        url = f"{self.base_url}/wp-json/wp/v2/posts/{wp_post_id}"

        try:
            response = await self._make_request(
                method="GET",
                url=url,
                auth=self.auth
            )

            return response.json()

        except BlogEngineHTTPError as e:
            self.logger.error("wp_post_get_failed", wp_post_id=wp_post_id, error=e.message)
            raise

    async def get_posts(
        self,
        status: str = "any",
        per_page: int = 20,
        page: int = 1,
        search: str = None
    ) -> list[dict]:
        """
        List WordPress posts.
        status: "publish" | "draft" | "any"
        Returns list of {id, title, status, link, date, modified, excerpt}
        """
        url = f"{self.base_url}/wp-json/wp/v2/posts"
        params = {
            "status": status,
            "per_page": per_page,
            "page": page
        }
        if search:
            params["search"] = search

        try:
            response = await self._make_request(
                method="GET",
                url=url,
                auth=self.auth,
                params=params
            )

            return response.json()

        except BlogEngineHTTPError as e:
            self.logger.error("wp_posts_get_failed", error=e.message)
            raise

    async def get_categories(self) -> list[dict]:
        """
        List all WordPress categories.
        Returns list of {id, name, slug, count}
        """
        url = f"{self.base_url}/wp-json/wp/v2/categories"
        params = {"per_page": 100}

        try:
            response = await self._make_request(
                method="GET",
                url=url,
                auth=self.auth,
                params=params
            )

            return response.json()

        except BlogEngineHTTPError as e:
            self.logger.error("wp_categories_get_failed", error=e.message)
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

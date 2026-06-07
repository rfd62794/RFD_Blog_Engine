"""
blog_engine/infra/base_api_handler.py

Base class for all API client handlers.
Borrowed from PrivyBot api/_handler.py and adapted for rfd-blog-engine.
"""

from typing import Callable
import asyncio
import httpx


class BaseAPIHandler:
    """
    Base class for all API client handlers.

    Subclass sets CACHE_PREFIX.
    All methods call self.call() not cache directly.
    Credentials loaded once via _get_client().
    """

    CACHE_PREFIX: str = ""  # set per subclass

    def _get_client(self):
        """Override to return authenticated client."""
        raise NotImplementedError

    def cache_key(self, suffix: str) -> str:
        """Namespaced cache key for this handler."""
        if not self.CACHE_PREFIX:
            raise NotImplementedError(
                f"{self.__class__.__name__} must set CACHE_PREFIX"
            )
        return f"{self.CACHE_PREFIX}_{suffix}"

    def call(
        self, suffix: str, params_hash: str, live_fn: Callable, stale_ok: bool = True
    ) -> dict:
        """
        All API calls go through here.
        Delegates to CacheManager.
        Subclasses never call cache directly.
        """
        from blog_engine.infra.cache_manager import cache
        from blog_engine.infra.rate_limits import rate_limits
        import logging
        import re

        logger = logging.getLogger("blog_engine.handler")
        key = self.cache_key(suffix)

        # Step 1 — fresh cache hit
        cached = cache.get(key, params_hash)
        if cached is not None:
            return cached

        # Step 2 — rate limit check
        if not rate_limits.can_call(self.CACHE_PREFIX):
            wait = rate_limits.time_until_available(self.CACHE_PREFIX)
            logger.warning(f"[handler] {self.CACHE_PREFIX} rate limited, {wait}s wait")

            stale = cache.get_or_stale(key, params_hash)
            if stale is not None:
                return stale

            return {
                "error": f"{self.CACHE_PREFIX} rate limited",
                "_rate_limited": True,
                "_retry_after": wait,
                "_stale": False
            }

        # Step 3 — live call
        try:
            result = live_fn()
            rate_limits.record_call(self.CACHE_PREFIX)
            cache.set(key, params_hash, result)
            return result

        except Exception as e:
            err_str = str(e)

            # Detect 429 and extract retry_after
            if "429" in err_str:
                retry_after = 60  # default

                # Try retry_after_seconds pattern
                m = re.search(r'retry.after.seconds[\'"\s:]+(\d+)', err_str, re.IGNORECASE)
                if m:
                    retry_after = int(m.group(1))
                else:
                    # Try Retry-After header pattern
                    m = re.search(r'retry.after[\'"\s:]+(\d+)', err_str, re.IGNORECASE)
                    if m:
                        retry_after = int(m.group(1))

                rate_limits.record_limit(self.CACHE_PREFIX, retry_after)

            # Log expected errors (403, 429) at DEBUG level to reduce noise
            if "403" in err_str or "429" in err_str:
                logger.debug(f"[handler] {self.CACHE_PREFIX} live failed (expected): {e}")
            else:
                logger.warning(f"[handler] {self.CACHE_PREFIX} live failed: {e}")

            if stale_ok:
                stale = cache.get_or_stale(key, params_hash)
                if stale is not None:
                    return stale

            return {
                "error": err_str,
                "_live_failed": True,
                "_stale": False
            }

    def hash(self, *args, **kwargs) -> str:
        """Convenience — delegates to cache.hash()."""
        from blog_engine.infra.cache_manager import cache

        return cache.hash(*args, **kwargs)


class BaseTool:
    """
    Base class for tool layer wrappers.
    Provides success() and error() helpers.
    """

    def success(self, data: dict, stale_result: dict = None) -> dict:
        """Return a successful result with optional stale notice."""
        from blog_engine.infra.cache_manager import cache
        
        result = {"ok": True, **data}
        
        if stale_result is not None:
            notice = cache.stale_notice(stale_result)
            if notice:
                result["_stale_notice"] = notice
        
        return result

    def error(self, message: str, code: int = None) -> dict:
        """Return an error result."""
        result = {"ok": False, "error": message}
        if code is not None:
            result["code"] = code
        return result

    def stale_notice(self, result: dict) -> str | None:
        """Extract stale notice from a result dict."""
        from blog_engine.infra.cache_manager import cache
        return cache.stale_notice(result)


class BlogEngineHTTPError(Exception):
    """HTTP error with status code and message."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP {status_code}: {message}")


# Add _make_request to BaseAPIHandler
async def _make_request(
    self,
    method: str,
    url: str,
    headers: dict = None,
    auth: tuple = None,
    json: dict = None,
    params: dict = None,
    max_attempts: int = 4,
    backoff_base: float = 2.0
) -> httpx.Response:
    """
    Makes HTTP request with exponential backoff retry.
    Retries on: 5xx, timeout, connection error.
    No retry on: 401, 400, 403, 404.
    Raises BlogEngineHTTPError after max_attempts exhausted.
    """
    if headers is None:
        headers = {}

    no_retry_codes = {400, 401, 403, 404}

    for attempt in range(1, max_attempts + 1):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    auth=auth,
                    json=json,
                    params=params,
                    timeout=30.0
                )
            
            # No retry on client errors
            if response.status_code in no_retry_codes:
                raise BlogEngineHTTPError(
                    response.status_code,
                    response.text or f"HTTP {response.status_code}"
                )
            
            # Success or server error
            if response.status_code < 500:
                return response
            
            # Server error - retry with backoff
            if attempt < max_attempts:
                backoff = backoff_base ** (attempt - 1)
                await asyncio.sleep(backoff)
                continue
            
            # Exhausted retries
            raise BlogEngineHTTPError(
                response.status_code,
                response.text or f"HTTP {response.status_code}"
            )
        
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            if attempt < max_attempts:
                backoff = backoff_base ** (attempt - 1)
                await asyncio.sleep(backoff)
                continue
            raise BlogEngineHTTPError(0, str(e))
        
        except BlogEngineHTTPError:
            raise  # Re-raise our own errors immediately
        
        except Exception as e:
            if attempt < max_attempts:
                backoff = backoff_base ** (attempt - 1)
                await asyncio.sleep(backoff)
                continue
            raise BlogEngineHTTPError(0, str(e))
    
    # Should not reach here
    raise BlogEngineHTTPError(0, "Max attempts exhausted")


# Bind the method to the class
BaseAPIHandler._make_request = _make_request

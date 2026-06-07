"""
blog_engine/infra/cache_manager.py

Cache manager for rfd-blog-engine.
Simplified from PrivyBot's infra/cache.py for standalone use.
Uses SQLite for cache storage instead of PrivyBot's complex cache system.
"""

import json
import time
import hashlib
import logging
import threading
from typing import Callable
from datetime import datetime

logger = logging.getLogger("blog_engine.cache")


class CacheManager:
    """
    Simple in-memory cache with TTL support.
    For MVP, this is sufficient. Can be upgraded to SQLite-backed cache later.
    """

    def __init__(self):
        self._cache = {}  # {(key, params_hash): (data, cached_at, ttl_seconds)}
        self._lock = threading.Lock()

    # ─── Canonical TTL registry ───────────
    # Source of truth for ALL cache TTLs.
    # Values in seconds.
    TTL = {
        "wordpress_posts": 300,  # 5min — drafts change frequently
        "wordpress_post": 300,  # 5min — individual post
        "devto_articles": 300,  # 5min
        "devto_article": 300,  # 5min
    }

    # ─── Staleness budget ─────────────────
    # How old is "too old" to show user.
    STALE_BUDGET = {
        "wordpress_posts": 300,
        "wordpress_post": 300,
        "devto_articles": 300,
        "devto_article": 300,
    }

    # ─── Core methods ─────────────────────

    def hash(self, *args, **kwargs) -> str:
        """
        Deterministic params hash.
        Use for fixed-param calls:
          cache.hash()  ← no params
          cache.hash("duckov")  ← one param
          cache.hash(days=7)  ← kwargs
        """
        key = json.dumps(
            {"args": list(args), "kwargs": kwargs},
            sort_keys=True, default=str
        )
        return hashlib.md5(key.encode()).hexdigest()

    def get(self, key: str, params_hash: str) -> dict | None:
        """
        Fresh cache hit only.
        Returns None if miss or expired.
        Does NOT return stale data.
        """
        cache_key = (key, params_hash)
        
        with self._lock:
            if cache_key not in self._cache:
                return None
            
            data, cached_at, ttl = self._cache[cache_key]
            age_seconds = time.time() - cached_at
            
            if age_seconds > ttl:
                # Expired
                del self._cache[cache_key]
                return None
            
            data["_stale"] = False
            return data

    def get_or_stale(self, key: str, params_hash: str) -> dict | None:
        """
        Fresh first. Stale if expired.
        None only if never cached.
        """
        fresh = self.get(key, params_hash)
        if fresh is not None:
            return fresh
        
        cache_key = (key, params_hash)
        with self._lock:
            if cache_key not in self._cache:
                return None
            
            data, cached_at, ttl = self._cache[cache_key]
            age_seconds = time.time() - cached_at
            age_minutes = int(age_seconds / 60)
            
            data["_stale"] = True
            data["_cached_at"] = datetime.fromtimestamp(cached_at).isoformat()
            data["_age_minutes"] = age_minutes
            return data

    def set(self, key: str, params_hash: str, data: dict) -> None:
        """
        Store with TTL from TTL policy.
        Unknown keys default to 3600s.
        """
        ttl = self.TTL.get(key, 3600)
        data["_stale"] = False
        
        with self._lock:
            self._cache[(key, params_hash)] = (data, time.time(), ttl)

    def call(self, key: str, params_hash: str, live_fn: Callable, stale_ok: bool = True) -> dict:
        """
        Main entry point for all API calls.

        1. Fresh cache hit → return immediately
        2. Live call succeeds → cache + return
        3. Live fails + stale_ok + stale exists → return stale with metadata
        4. Live fails, no stale → error dict

        TTL comes from self.TTL[key].
        """
        # Step 1 — fresh hit
        cached = self.get(key, params_hash)
        if cached is not None:
            logger.debug(f"[cache] HIT {key}")
            return cached

        # Step 2 — live call
        start = time.time()
        try:
            result = live_fn()
            duration_ms = int((time.time() - start) * 1000)

            if not isinstance(result, dict):
                result = {"value": result}

            self.set(key, params_hash, result)

            logger.debug(f"[cache] LIVE {key} ({duration_ms}ms)")
            return result

        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            logger.warning(f"[cache] LIVE FAIL {key}: {e}")

            # Step 3 — stale fallback
            if stale_ok:
                stale = self.get_or_stale(key, params_hash)
                if stale is not None:
                    logger.info(
                        f"[cache] STALE {key} ({stale.get('_age_minutes', '?')}min)"
                    )
                    return stale

            # Step 4 — total failure
            return {"error": str(e), "_live_failed": True, "_stale": False}

    def stale_notice(self, result: dict) -> str | None:
        """
        Human-readable staleness notice.
        Returns None if fresh data.
        """
        if not result.get("_stale"):
            return None

        age = result.get("_age_minutes", 0)
        ts = result.get("_cached_at", "")[:16]

        if age < 60:
            age_str = f"{age}m ago"
        elif age < 1440:
            age_str = f"{age // 60}h ago"
        else:
            age_str = f"{age // 1440}d ago"

        return f"⚠️ Data from {age_str} ({ts})"

    def invalidate(self, key: str, params_hash: str = None) -> None:
        """
        Clear cached data.
        params_hash=None clears all entries for that key.
        """
        with self._lock:
            if params_hash:
                cache_key = (key, params_hash)
                if cache_key in self._cache:
                    del self._cache[cache_key]
            else:
                # Clear all entries for this key
                keys_to_delete = [k for k in self._cache.keys() if k[0] == key]
                for k in keys_to_delete:
                    del self._cache[k]
        logger.info(f"[cache] INVALIDATED {key}")


# ─── Singleton ────────────────────────────
# All other layers import this instance.
# from blog_engine.infra.cache_manager import cache
cache = CacheManager()

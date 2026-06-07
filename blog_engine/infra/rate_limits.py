"""
blog_engine/infra/rate_limits.py

Rate limit manager for rfd-blog-engine.
Simplified from PrivyBot's infra/rate_limits.py for standalone use.
"""

import logging
from datetime import datetime, timedelta
import threading

logger = logging.getLogger("blog_engine.rate_limits")


class RateLimitManager:
    """
    Simple in-memory rate limit tracking.
    For MVP, this is sufficient. Can be upgraded to SQLite-backed tracking later.
    """

    # ─── Known limits per API ─────────────
    LIMITS = {
        "wordpress": {
            "requests_per_minute": 60,
        },
        "devto": {
            "requests_per_minute": 60,
        },
    }

    def __init__(self):
        self._state = {}  # {api: {"last_call_at": timestamp, "calls_this_minute": int, "last_429_at": timestamp, "retry_after_seconds": int}}
        self._lock = threading.Lock()

    def can_call(self, api: str) -> bool:
        """
        True if safe to make a live call now.
        
        Checks in order:
        1. Explicit 429 cooldown active?
        2. Per-minute rate exceeded?
        
        Returns True if all checks pass.
        Unknown APIs always return True.
        """
        with self._lock:
            state = self._state.get(api, {})
            now = datetime.now()
            
            # Check 1 — 429 cooldown
            if state.get("last_429_at"):
                last_429 = state["last_429_at"]
                retry_after = state.get("retry_after_seconds", 60)
                cooldown_until = last_429 + timedelta(seconds=retry_after)
                if now < cooldown_until:
                    remaining = int((cooldown_until - now).total_seconds())
                    logger.debug(f"[rate] {api} in cooldown ({remaining}s remaining)")
                    return False
            
            # Check 2 — per-minute limit
            limits = self.LIMITS.get(api, {})
            rpm = limits.get("requests_per_minute")
            
            if rpm and state.get("last_call_at"):
                last_call = state["last_call_at"]
                if (now - last_call).total_seconds() < 60:
                    if state.get("calls_this_minute", 0) >= rpm:
                        logger.warning(f"[rate] {api} minute limit reached ({rpm}/min)")
                        return False
            
            return True

    def record_call(self, api: str, cost: int = 1) -> None:
        """
        Record a successful API call.
        Updates rolling counters.
        """
        with self._lock:
            now = datetime.now()
            state = self._state.get(api, {})
            
            # Reset minute counter if >60s
            calls_this_minute = state.get("calls_this_minute", 0)
            if state.get("last_call_at"):
                last = state["last_call_at"]
                if (now - last).total_seconds() >= 60:
                    calls_this_minute = 0
            
            self._state[api] = {
                **state,
                "calls_this_minute": calls_this_minute + 1,
                "last_call_at": now,
            }

    def record_limit(self, api: str, retry_after: int = 60) -> None:
        """
        Record a 429 response.
        Sets cooldown.
        """
        with self._lock:
            now = datetime.now()
            state = self._state.get(api, {})
            self._state[api] = {
                **state,
                "last_429_at": now,
                "retry_after_seconds": retry_after
            }
            logger.warning(f"[rate] {api} 429 recorded. Retry after {retry_after}s")

    def time_until_available(self, api: str) -> int:
        """
        Seconds until next call allowed.
        Returns 0 if available now.
        """
        with self._lock:
            state = self._state.get(api, {})
            if not state.get("last_429_at"):
                return 0
            
            now = datetime.now()
            last_429 = state["last_429_at"]
            retry_after = state.get("retry_after_seconds", 60)
            cooldown_until = last_429 + timedelta(seconds=retry_after)
            
            if now >= cooldown_until:
                return 0
            return int((cooldown_until - now).total_seconds())


# Singleton instance
rate_limits = RateLimitManager()

"""
blog_engine/infra/db_manager.py

SQLite database manager for rfd-blog-engine.
Manages connections, retries, and centralized SQL execution.
Simplified from PrivyBot's infra/db/manager.py for standalone use.
"""

import time
import sqlite3
import threading
from pathlib import Path
from typing import Tuple, Optional

# ─── Database connection ─────────────────────

_DB_PATH = Path(__file__).parent.parent.parent / "data" / "blog_engine.db"
_conn = None
_lock = threading.Lock()


def _get_connection() -> sqlite3.Connection:
    """Get or create the database connection with WAL mode."""
    global _conn
    if _conn is None:
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        _conn.execute("PRAGMA journal_mode = WAL")
        _conn.execute("PRAGMA foreign_keys = ON")
        _conn.execute("PRAGMA synchronous = NORMAL")
    return _conn


def _exec(sql: str, params: Tuple = (), commit: bool = False) -> sqlite3.Cursor:
    """
    Execute SQL directly on the connection.
    Not retry-safe — use DBManager.exec() for automatic retries.
    """
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(sql, params)
    if commit:
        conn.commit()
    return cursor


class DBManager:
    """
    Single owner of all database access.

    Wraps _exec() with automatic retry on lock errors.
    All database access should go through db.exec().
    """

    def __init__(self, max_retries: int = 10, base_backoff: float = 0.1):
        self.max_retries = max_retries
        self.base_backoff = base_backoff

    def exec(
        self, sql: str, params: Tuple = (), commit: bool = False
    ) -> sqlite3.Cursor:
        """
        Execute SQL with automatic retry on lock errors.

        Args:
            sql: SQL statement to execute
            params: Parameters for the SQL statement
            commit: Whether to commit after execution

        Returns:
            sqlite3.Cursor

        Raises:
            sqlite3.OperationalError: If all retries fail
        """
        for attempt in range(self.max_retries):
            try:
                return _exec(sql, params, commit)
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and attempt < self.max_retries - 1:
                    # Exponential backoff
                    backoff = self.base_backoff * (2 ** attempt)
                    time.sleep(backoff)
                    continue
                # Re-raise if not a lock error or retries exhausted
                raise

    def exec_many(
        self, sql: str, params_list: list[Tuple], commit: bool = False
    ) -> None:
        """
        Execute SQL with multiple parameter sets.

        Args:
            sql: SQL statement to execute
            params_list: List of parameter tuples
            commit: Whether to commit after execution
        """
        with _lock:
            cursor = _get_connection().cursor()
            cursor.executemany(sql, params_list)
            if commit:
                _get_connection().commit()

    def get_connection(self) -> sqlite3.Connection:
        """Get the current database connection."""
        return _get_connection()

    def initialize_schema(self) -> None:
        """Initialize the database schema from SDD §2."""
        schema_sql = """
        PRAGMA foreign_keys = ON;
        PRAGMA journal_mode = WAL;

        -- Post thread relationships
        CREATE TABLE IF NOT EXISTS post_threads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS post_thread_members (
            post_id TEXT NOT NULL,
            thread_id INTEGER NOT NULL,
            sequence INTEGER,
            PRIMARY KEY (post_id, thread_id),
            FOREIGN KEY (thread_id) REFERENCES post_threads(id)
        );

        -- Post context memory (RFD Content Frame slots)
        CREATE TABLE IF NOT EXISTS post_context (
            post_id TEXT PRIMARY KEY,
            raw_extraction TEXT,
            frame_moment TEXT,
            frame_surprise TEXT,
            frame_struggle TEXT,
            frame_lesson TEXT,
            frame_next TEXT,
            related_posts TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Draft revision history
        CREATE TABLE IF NOT EXISTS draft_revisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id TEXT NOT NULL,
            revision_number INTEGER NOT NULL,
            content TEXT NOT NULL,
            saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            saved_by TEXT,
            UNIQUE (post_id, revision_number)
        );

        -- Publish log (idempotency source of truth)
        CREATE TABLE IF NOT EXISTS publish_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            status TEXT NOT NULL,
            platform_id TEXT,
            platform_url TEXT,
            error_message TEXT,
            published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (post_id, platform, status)
                ON CONFLICT IGNORE
        );

        -- Indexes for common query patterns
        CREATE INDEX IF NOT EXISTS idx_draft_revisions_post
            ON draft_revisions(post_id, revision_number);

        CREATE INDEX IF NOT EXISTS idx_publish_log_post
            ON publish_log(post_id, platform);

        CREATE INDEX IF NOT EXISTS idx_thread_members_thread
            ON post_thread_members(thread_id);
        """
        
        with _lock:
            conn = _get_connection()
            conn.executescript(schema_sql)
            conn.commit()


# Singleton instance
db = DBManager()

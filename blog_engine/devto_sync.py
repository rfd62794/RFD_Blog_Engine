"""
blog_engine/devto_sync.py

Idempotent Dev.to sync job.

Syndicates newly-published WordPress posts to Dev.to with verified canonicals.
Designed for daily scheduled runs via Tower / Task Scheduler.

Rules (locked design):
- Canonical = live WP `link` field (pretty permalink), verified HTTP 200 before any write.
- Sync window: only posts published on/after DEVTO_SYNC_START_DATE.
- Backfill is a separate explicit mode, never automatic.
- Idempotent: posts with an existing devto_id record are skipped.
- Validation gate: excerpt and canonical checks before syndication.
- --dry-run: prints action plan, no writes.
"""

import asyncio
import os
import sys
import argparse
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import httpx

from blog_engine.infra.db_manager import DBManager
from blog_engine.infra.logger import get_logger
from blog_engine.api.devto import DevToHandler
from blog_engine.api.wordpress import WordPressHandler

logger = get_logger(__name__)

# Config
DEVTO_SYNC_START_DATE_ENV = "DEVTO_SYNC_START_DATE"
DEFAULT_START_DATE = "2026-06-11"  # date this module was committed


def _get_start_date() -> date:
    """Read DEVTO_SYNC_START_DATE from env, fall back to DEFAULT_START_DATE."""
    raw = os.getenv(DEVTO_SYNC_START_DATE_ENV, DEFAULT_START_DATE)
    return date.fromisoformat(raw)


def _get_wp_handler() -> WordPressHandler:
    wp_url = os.getenv("WORDPRESS_URL", "").rstrip("/")
    wp_user = os.getenv("WORDPRESS_USER", "")
    wp_pass = os.getenv("WORDPRESS_APP_PASSWORD", "")
    db = DBManager()
    return WordPressHandler(db, wp_url, wp_user, wp_pass)


def _get_devto_handler() -> DevToHandler:
    api_key = os.getenv("DEVTO_API_KEY", "")
    db = DBManager()
    return DevToHandler(db, api_key)


def _get_db() -> DBManager:
    return DBManager()


async def _verify_canonical(url: str) -> bool:
    """Return True if url returns HTTP 200. Never raises — returns False on any error."""
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, follow_redirects=False, timeout=10.0)
            return r.status_code == 200
    except Exception:
        return False


def _has_devto_record(db: DBManager, wp_post_id: int) -> bool:
    """
    Check publish_log for an existing devto success record by wp_post_id.
    We store wp_post_id as platform_id for wordpress; for devto we key by post_id.
    Checks both by engine post_id (from wordpress log) and direct devto success row.
    """
    # Find engine post_id from wordpress log
    row = db.exec(
        "SELECT post_id FROM publish_log WHERE platform='wordpress' AND platform_id=? AND status='success'",
        (str(wp_post_id),),
    ).fetchone()
    if not row:
        return False
    engine_post_id = row[0]
    devto_row = db.exec(
        "SELECT 1 FROM publish_log WHERE post_id=? AND platform='devto' AND status='success'",
        (engine_post_id,),
    ).fetchone()
    return devto_row is not None


def _record_sync_action(
    db: DBManager,
    wp_post_id: int,
    action: str,
    reason: str,
    devto_id: Optional[int] = None,
    devto_url: Optional[str] = None,
) -> None:
    """
    Write a devto_sync_log entry.
    action: 'created' | 'skipped_existing' | 'refused_validation' | 'refused_canonical' | 'skipped_window'
    """
    db.exec(
        """
        INSERT INTO devto_sync_log (wp_post_id, action, reason, devto_id, devto_url, synced_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            wp_post_id,
            action,
            reason,
            str(devto_id) if devto_id else None,
            devto_url,
            datetime.now(timezone.utc).isoformat(),
        ),
        commit=True,
    )


def _ensure_sync_log_table(db: DBManager) -> None:
    """Create devto_sync_log table if not exists."""
    db.exec(
        """
        CREATE TABLE IF NOT EXISTS devto_sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wp_post_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            reason TEXT,
            devto_id TEXT,
            devto_url TEXT,
            synced_at TEXT NOT NULL
        )
        """,
        commit=True,
    )


async def _build_action_plan(
    wp_posts: list[dict],
    db: DBManager,
    start_date: date,
) -> list[dict]:
    """
    For each WP post, determine the action without executing it.
    Returns list of action dicts:
      {wp_post_id, title, link, publish_date, action, reason}
    action: 'would_syndicate' | 'skip_existing' | 'skip_window' | 'refuse_canonical' | 'refuse_validation'
    """
    plan = []

    for post in wp_posts:
        wp_id = post["id"]
        title = post.get("title", {}).get("rendered", "") if isinstance(post.get("title"), dict) else str(post.get("title", ""))
        link = post.get("link", "")
        date_str = post.get("date", "")
        excerpt_rendered = post.get("excerpt", {}).get("rendered", "") if isinstance(post.get("excerpt"), dict) else ""

        # Parse publish date
        try:
            post_date = datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
        except Exception:
            post_date = None

        entry = {
            "wp_post_id": wp_id,
            "title": title,
            "link": link,
            "publish_date": str(post_date),
            "action": None,
            "reason": None,
        }

        # Check sync window
        if post_date is None or post_date < start_date:
            entry["action"] = "skip_window"
            entry["reason"] = f"publish_date {post_date} before start_date {start_date}"
            plan.append(entry)
            continue

        # Check existing devto record
        if _has_devto_record(db, wp_id):
            entry["action"] = "skip_existing"
            entry["reason"] = "devto success record exists in publish_log"
            plan.append(entry)
            continue

        # Validate canonical: must be pretty permalink (not ?p=)
        if "?p=" in link or "?page_id=" in link:
            entry["action"] = "refuse_validation"
            entry["reason"] = f"slug is query-string fallback: {link}"
            plan.append(entry)
            continue

        # Validate excerpt
        if not excerpt_rendered or not excerpt_rendered.strip():
            entry["action"] = "refuse_validation"
            entry["reason"] = "excerpt is empty"
            plan.append(entry)
            continue

        # Verify canonical returns 200
        canonical_ok = await _verify_canonical(link)
        if not canonical_ok:
            entry["action"] = "refuse_canonical"
            entry["reason"] = f"canonical {link} did not return HTTP 200"
            plan.append(entry)
            continue

        entry["action"] = "would_syndicate"
        entry["reason"] = f"canonical verified, excerpt present, within window"
        plan.append(entry)

    return plan


async def run_sync(dry_run: bool = False) -> dict:
    """
    Main sync entry point.

    Returns summary dict:
      {created, skipped_existing, refused, dry_run, posts: [action dicts]}
    """
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

    api_key = os.getenv("DEVTO_API_KEY", "")
    if not api_key:
        return {"error": "DEVTO_API_KEY not configured"}

    start_date = _get_start_date()
    db = _get_db()
    _ensure_sync_log_table(db)

    wp = _get_wp_handler()

    # Enumerate published posts from live WP listing (not publish_log)
    wp_posts = await wp.get_posts(status="publish", per_page=100)

    plan = await _build_action_plan(wp_posts, db, start_date)

    summary = {
        "dry_run": dry_run,
        "start_date": str(start_date),
        "total_wp_posts": len(wp_posts),
        "created": 0,
        "skipped_existing": 0,
        "skipped_window": 0,
        "refused": 0,
        "posts": plan,
    }

    for entry in plan:
        action = entry["action"]

        if action == "skip_existing":
            summary["skipped_existing"] += 1
            if not dry_run:
                _record_sync_action(db, entry["wp_post_id"], "skipped_existing", entry["reason"])

        elif action in ("refuse_canonical", "refuse_validation"):
            summary["refused"] += 1
            if not dry_run:
                _record_sync_action(db, entry["wp_post_id"], action, entry["reason"])

        elif action == "skip_window":
            summary["skipped_window"] += 1

        elif action == "would_syndicate":
            if dry_run:
                # Dry run: just count, no writes
                summary["created"] += 1
            else:
                # Find engine post_id from wordpress publish_log
                row = db.exec(
                    "SELECT post_id FROM publish_log WHERE platform='wordpress' AND platform_id=? AND status='success'",
                    (str(entry["wp_post_id"]),),
                ).fetchone()

                if not row:
                    entry["action"] = "refuse_validation"
                    entry["reason"] = "no engine post_id found in publish_log for this wp_post_id"
                    summary["refused"] += 1
                    _record_sync_action(db, entry["wp_post_id"], "refused_validation", entry["reason"])
                    continue

                engine_post_id = row[0]

                # Fetch full post for content
                wp_full = await wp.get_post(entry["wp_post_id"])
                content = wp_full.get("content", {}).get("rendered", "") if isinstance(wp_full.get("content"), dict) else ""
                title = wp_full.get("title", {}).get("rendered", "") if isinstance(wp_full.get("title"), dict) else ""
                tags_raw = wp_full.get("tags", [])
                # Only send string tags (devto expects tag slugs); int IDs are WP IDs, not dev.to tags
                tags = [t for t in tags_raw if isinstance(t, str)]

                devto = _get_devto_handler()
                result = await devto.create_article(
                    post_id=engine_post_id,
                    title=title,
                    body_markdown=content,
                    canonical_url=entry["link"],
                    tags=tags,
                    published=True,
                )

                if "error" in result:
                    entry["action"] = "refused_api_error"
                    entry["reason"] = result["error"]
                    summary["refused"] += 1
                    _record_sync_action(db, entry["wp_post_id"], "refused_api_error", result["error"])
                else:
                    entry["devto_id"] = result["devto_id"]
                    entry["devto_url"] = result["devto_url"]
                    summary["created"] += 1
                    _record_sync_action(
                        db,
                        entry["wp_post_id"],
                        "created",
                        "syndicated successfully",
                        devto_id=result["devto_id"],
                        devto_url=result["devto_url"],
                    )
                    logger.info(
                        "devto_sync.created",
                        wp_post_id=entry["wp_post_id"],
                        devto_id=result["devto_id"],
                        devto_url=result["devto_url"],
                    )

    return summary


async def devto_sync_dry_run() -> dict:
    """
    MCP tool: returns the full sync action plan without writing anything.
    Shows which posts would be syndicated, skipped, or refused and why.
    """
    return await run_sync(dry_run=True)


def _print_plan(summary: dict) -> None:
    """Print dry-run plan to stdout."""
    print(f"\n=== Dev.to Sync Dry Run ===")
    print(f"start_date:      {summary['start_date']}")
    print(f"total_wp_posts:  {summary['total_wp_posts']}")
    print(f"would_syndicate: {summary['created']}")
    print(f"skip_existing:   {summary['skipped_existing']}")
    print(f"skip_window:     {summary['skipped_window']}")
    print(f"refused:         {summary['refused']}")
    print()
    for p in summary["posts"]:
        action_label = p["action"].upper().ljust(20)
        print(f"  [{action_label}] WP {p['wp_post_id']:>4}  {p['title'][:55]}")
        print(f"                         {p['reason']}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dev.to sync job for rfd-blog-engine")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without writing")
    parser.add_argument(
        "--backfill",
        nargs="+",
        metavar="WP_ID",
        help="Explicit backfill mode: syndicate specific WP post IDs only (human-invoked)",
    )
    args = parser.parse_args()

    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

    result = asyncio.run(run_sync(dry_run=args.dry_run))

    if args.dry_run:
        _print_plan(result)
    else:
        print(f"Sync complete: created={result['created']} skipped={result['skipped_existing']} refused={result['refused']}")

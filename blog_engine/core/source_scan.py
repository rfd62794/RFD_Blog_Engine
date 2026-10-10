"""
blog_engine/core/source_scan.py

Daily draft source: turns real shipped work (recent commits) in an allow-list
of repos into inventory candidates. Deterministic — no model calls; generation
stays in PostGenerator. See docs/superpowers/specs/2026-09-27-daily-draft-loop.md
Stage A.
"""

import logging
import os
import subprocess
from typing import Optional

from blog_engine.core.inventory import InventoryManager

# stdlib logging, not structlog: unconfigured structlog prints to stdout, and
# this module feeds the `generate-daily` CLI whose stdout is a machine-read
# sentinel (NO_CANDIDATES) — warnings must stay on stderr.
logger = logging.getLogger("blog_engine.source_scan")

# Absolute repo paths this scan is allowed to read. Override with the
# SOURCE_SCAN_REPOS env var (comma-separated absolute paths). Robert expands
# this list — never scan a path that is not in it.
ALLOWED_REPOS: list[str] = [
    "C:/Github/RFD_Blog_Engine",
    "C:/Github/AgentFlow",
]

# Commit subjects that are bookkeeping, not shipped work.
_SKIP_PREFIXES = ("Merge ", "Queue: ")

_TITLE_LIMIT = 72


def _allowed_repos() -> list[str]:
    """Resolve the effective allow-list: SOURCE_SCAN_REPOS env var if set, else ALLOWED_REPOS."""
    env = os.getenv("SOURCE_SCAN_REPOS")
    if env:
        return [p.strip() for p in env.split(",") if p.strip()]
    return list(ALLOWED_REPOS)


def _title_from_subject(subject: str) -> str:
    """Derive a post title from a commit subject, truncated."""
    subject = subject.strip()
    if len(subject) <= _TITLE_LIMIT:
        return subject
    return subject[: _TITLE_LIMIT - 3].rstrip() + "..."


def _full_sha(repo: str, short_sha: str) -> str:
    """Resolve a short sha to the full sha; falls back to the short sha on failure."""
    proc = subprocess.run(
        ["git", "-C", repo, "rev-parse", short_sha],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        logger.warning("source_scan.rev_parse_failed repo=%s ref=%s", repo, short_sha)
        return short_sha
    return proc.stdout.strip()


def scan_recent_activity(
    repos: Optional[list[str]] = None,
    since_days: int = 2,
    max_candidates: int = 2,
) -> list[dict]:
    """
    Scan recent git history in allowed repos and return draft candidates,
    most recent first, at most max_candidates.

    Each candidate: {post_id, title, notes, category, tags, source_repo, source_ref}.
    Returns [] when nothing qualifies — never fabricates a candidate.
    """
    allowed = _allowed_repos()
    targets = allowed if repos is None else repos

    candidates: list[dict] = []
    for repo in targets:
        if len(candidates) >= max_candidates:
            break
        if repo not in allowed:
            logger.warning("source_scan.repo_not_allowed repo=%s", repo)
            continue

        proc = subprocess.run(
            [
                "git", "-C", repo, "log",
                f"--since={since_days} days ago",
                "--oneline", "--no-merges",
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            logger.warning(
                "source_scan.git_log_failed repo=%s stderr=%s",
                repo,
                proc.stderr.strip(),
            )
            continue

        for line in proc.stdout.splitlines():
            if len(candidates) >= max_candidates:
                break
            line = line.strip()
            if not line:
                continue
            short_sha, _, subject = line.partition(" ")
            if not short_sha or not subject:
                continue
            if subject.startswith(_SKIP_PREFIXES):
                continue
            candidates.append({
                "post_id": f"src-{short_sha}",
                "title": _title_from_subject(subject),
                "notes": subject,
                "category": "building",
                "tags": [],
                "source_repo": repo,
                "source_ref": _full_sha(repo, short_sha),
            })

    return candidates


def register_candidates(
    candidates: list[dict],
    inventory: InventoryManager,
) -> list[str]:
    """
    Register each candidate in the inventory unless its post_id already exists.
    Idempotent — safe to run daily. Returns newly-registered post_ids.
    """
    registered: list[str] = []
    for candidate in candidates:
        post_id = candidate["post_id"]
        if inventory.get_post(post_id) is not None:
            continue
        inventory.add_post(
            post_id=post_id,
            title=candidate["title"],
            category=candidate["category"],
            notes=candidate["notes"],
            tags=candidate["tags"],
        )
        registered.append(post_id)
    return registered

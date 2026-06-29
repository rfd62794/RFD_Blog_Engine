"""
scripts/backfill_wp_urls.py

One-shot backfill: for every draft JSON with a ?p= wp_url, fetch the real
permalink from the WordPress REST API and patch the draft JSON in place.

Usage: uv run python scripts/backfill_wp_urls.py
"""

import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

import aiohttp

WP_URL = os.getenv("WORDPRESS_URL", "").rstrip("/")
WP_USER = os.getenv("WORDPRESS_USER", "")
WP_APP_PASSWORD = os.getenv("WORDPRESS_APP_PASSWORD", "")
DRAFTS_DIR = Path(__file__).parent.parent / "data" / "drafts"


async def fetch_wp_permalink(session: aiohttp.ClientSession, wp_post_id: int) -> str | None:
    url = f"{WP_URL}/wp-json/wp/v2/posts/{wp_post_id}"
    headers = {
        "Authorization": "Basic " + __import__("base64").b64encode(
            f"{WP_USER}:{WP_APP_PASSWORD}".encode()
        ).decode()
    }
    try:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("link", "")
            elif resp.status == 404:
                return None
            else:
                print(f"  WP API {resp.status} for post {wp_post_id}")
                return None
    except Exception as e:
        print(f"  Error fetching post {wp_post_id}: {e}")
        return None


def atomic_write(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    if path.exists():
        path.unlink()
    tmp.rename(path)


async def main():
    draft_paths = sorted(DRAFTS_DIR.glob("*.json"))

    # Collect drafts needing backfill
    to_fix = []
    for path in draft_paths:
        with open(path, encoding="utf-8") as f:
            draft = json.load(f)
        wp_url = draft.get("wp_url", "")
        wp_post_id = draft.get("wp_post_id")
        if wp_url and "?p=" in wp_url and wp_post_id:
            to_fix.append((path, draft, wp_post_id))

    print(f"Drafts with ?p= URLs: {len(to_fix)} / {len(draft_paths)}")
    print()

    if not to_fix:
        print("Nothing to fix.")
        return

    results = {"fixed": [], "not_found": [], "skipped": [], "errors": []}

    async with aiohttp.ClientSession() as session:
        for path, draft, wp_post_id in to_fix:
            post_id = draft.get("post_id", path.stem)
            old_url = draft["wp_url"]

            new_link = await fetch_wp_permalink(session, wp_post_id)

            if new_link is None:
                print(f"  SKIP  {post_id} (wp_post_id={wp_post_id}) — 404 or error")
                results["not_found"].append(post_id)
                continue

            if "?p=" in new_link:
                print(f"  SKIP  {post_id} — WP still returning ?p= URL (permalink not set)")
                results["skipped"].append(post_id)
                continue

            if new_link == old_url:
                print(f"  OK    {post_id} — already correct: {new_link}")
                results["skipped"].append(post_id)
                continue

            # Patch draft JSON
            draft["wp_url"] = new_link
            atomic_write(path, draft)
            print(f"  FIXED {post_id}: {old_url}  →  {new_link}")
            results["fixed"].append({"post_id": post_id, "old": old_url, "new": new_link})

    print()
    print("=" * 60)
    print(f"Fixed:      {len(results['fixed'])}")
    print(f"Not found:  {len(results['not_found'])}")
    print(f"Skipped:    {len(results['skipped'])}")
    print()
    if results["not_found"]:
        print("Not found (WP post may be deleted or unpublished):")
        for p in results["not_found"]:
            print(f"  - {p}")


if __name__ == "__main__":
    asyncio.run(main())

"""
blog_engine/wp_identity.py

Align the WordPress site identity with rfditservices.com (site redesign SEO spec §5):
site title, tagline, author display name and author URL.

Usage:
  python -m blog_engine.wp_identity            # dry run: prints planned changes
  python -m blog_engine.wp_identity --apply    # writes via the WordPress REST API
Uses WORDPRESS_URL / WORDPRESS_USER / WORDPRESS_APP_PASSWORD from .env. Never prints secrets.
"""
import argparse
import os
import sys
from pathlib import Path

import httpx

TARGET = {
    "title": "Robert Floyd Dugger — Writing",
    "description": "Practical notes on contact-center automation, dialer operations and AI-assisted engineering by Robert Floyd Dugger, Automation Engineer.",
    "name": "Robert Floyd Dugger",
    "url": "https://rfditservices.com/about/",
}


def plan_changes(current_settings: dict, current_user: dict) -> list[dict]:
    """Return the fields whose current value differs from TARGET."""
    changes = []
    for field in ("title", "description"):
        if (current_settings.get(field) or "") != TARGET[field]:
            changes.append({"endpoint": "settings", "field": field, "from": current_settings.get(field), "to": TARGET[field]})
    for field in ("name", "url"):
        if (current_user.get(field) or "") != TARGET[field]:
            changes.append({"endpoint": "users/me", "field": field, "from": current_user.get(field), "to": TARGET[field]})
    return changes


def main() -> int:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    base = os.getenv("WORDPRESS_URL", "").rstrip("/") + "/wp-json/wp/v2"
    auth = (os.getenv("WORDPRESS_USER", ""), os.getenv("WORDPRESS_APP_PASSWORD", ""))
    with httpx.Client(auth=auth, timeout=20) as client:
        settings = client.get(f"{base}/settings").raise_for_status().json()
        user = client.get(f"{base}/users/me", params={"context": "edit"}).raise_for_status().json()
        changes = plan_changes(settings, user)
        for c in changes:
            print(f"{'APPLY' if args.apply else 'PLAN '} {c['endpoint']}.{c['field']}: {c['from']!r} -> {c['to']!r}")
        if args.apply:
            s = {c["field"]: c["to"] for c in changes if c["endpoint"] == "settings"}
            u = {c["field"]: c["to"] for c in changes if c["endpoint"] == "users/me"}
            if s:
                client.post(f"{base}/settings", json=s).raise_for_status()
            if u:
                client.post(f"{base}/users/me", json=u).raise_for_status()
        print(f"{len(changes)} change(s){'' if args.apply else ' planned (dry run)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
import httpx

load_dotenv(dotenv_path=Path("C:/Github/RFD_Blog_Engine/.env"))

wp_url = os.getenv("WORDPRESS_URL", "").rstrip("/")
wp_user = os.getenv("WORDPRESS_USER", "")
wp_pass = os.getenv("WORDPRESS_APP_PASSWORD", "")

print(f"env_path: C:/Github/RFD_Blog_Engine/.env")
print(f"WORDPRESS_URL: {wp_url}")
print(f"auth_user: {wp_user}")
print()


async def test():
    auth = (wp_user, wp_pass)
    for wp_id in [92, 115]:
        url = f"{wp_url}/wp-json/wp/v2/posts/{wp_id}"
        print(f"--- WP ID {wp_id} ---")
        print(f"request_url: {url}")
        async with httpx.AsyncClient() as c:
            r = await c.get(url, auth=auth, timeout=15)
            print(f"status_code: {r.status_code}")
            if r.status_code == 200:
                d = r.json()
                title = d.get("title", {}).get("rendered", "")
                excerpt_raw = d.get("excerpt", {}).get("rendered", "")
                print(f"title: {title}")
                print(f"link: {d.get('link')}")
                print(f"tags: {d.get('tags')}")
                print(f"categories: {d.get('categories')}")
                print(f"featured_media: {d.get('featured_media')}")
                print(f"excerpt_empty: {not bool(excerpt_raw.strip())}")
            else:
                print(f"body: {r.text[:300]}")
        print()

    # Also enumerate all publish+future posts for the audit
    print("--- ALL PUBLISHED/FUTURE POSTS ---")
    for status in ["publish", "future"]:
        url = f"{wp_url}/wp-json/wp/v2/posts"
        async with httpx.AsyncClient() as c:
            r = await c.get(url, auth=auth, params={"status": status, "per_page": 100}, timeout=15)
            print(f"status={status} response_code={r.status_code}")
            if r.status_code == 200:
                posts = r.json()
                for p in posts:
                    excerpt_raw = p.get("excerpt", {}).get("rendered", "")
                    print(
                        f"  id={p['id']} tags={p.get('tags')} cats={p.get('categories')} "
                        f"featured={p.get('featured_media')} excerpt_empty={not bool(excerpt_raw.strip())} "
                        f"slug={p.get('slug')} link={p.get('link')}"
                    )


asyncio.run(test())

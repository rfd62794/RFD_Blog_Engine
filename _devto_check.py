import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
import httpx

load_dotenv(dotenv_path=Path("C:/Github/RFD_Blog_Engine/.env"))

api_key = os.getenv("DEVTO_API_KEY", "")
print(f"DEVTO_API_KEY present: {bool(api_key)}")


async def check():
    url = "https://dev.to/api/articles/3844728"
    headers = {"api-key": api_key}
    async with httpx.AsyncClient() as c:
        r = await c.get(url, headers=headers, timeout=15)
        print(f"status_code: {r.status_code}")
        if r.status_code == 200:
            d = r.json()
            print(f"canonical_url: {d.get('canonical_url')!r}")
            print(f"url: {d.get('url')!r}")
            print(f"title: {d.get('title')!r}")
        else:
            print(f"body: {r.text[:500]}")

asyncio.run(check())

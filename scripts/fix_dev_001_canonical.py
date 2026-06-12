"""
scripts/fix_dev_001_canonical.py

One-shot script to fix Dev.to article 3844728 (dev-001) canonical URL.
Updates canonical_url from incorrect /test/ path to live blog URL.

Usage: uv run python scripts/fix_dev_001_canonical.py
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

from blog_engine.tools.validate_metadata import fix_devto_canonical


async def main():
    """Fix dev-001 canonical URL."""
    
    # Get correct canonical URL from engine data
    # dev-001's live URL: https://blog.rfditservices.com/same-game-20-years/
    # (Based on post title "I built the same game for 20 years without knowing it")
    
    # Read current article state first
    # From live WP check: https://blog.rfditservices.com/2026/06/07/i-built-the-same-game-for-20-years-without-knowing-it/
    correct_canonical = "https://blog.rfditservices.com/2026/06/07/i-built-the-same-game-for-20-years-without-knowing-it/"
    
    print(f"Fixing dev-001 (article 3844728) canonical URL...")
    print(f"Setting canonical to: {correct_canonical}")
    
    result = await fix_devto_canonical("3844728", correct_canonical)
    
    print(f"\nResult:")
    print(f"  Article ID: {result['article_id']}")
    print(f"  Before: {result['before']}")
    print(f"  After: {result['after']}")
    print(f"  Expected: {result['expected']}")
    print(f"  Success: {result['success']}")
    
    return result


if __name__ == "__main__":
    asyncio.run(main())

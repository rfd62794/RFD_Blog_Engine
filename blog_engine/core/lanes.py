"""
blog_engine/core/lanes.py

Lane mapping for rfd-blog-engine, from docs/notes/2026-09-23-blog-redesign-plan.md
section 4.1. A post's lane is derived from its category: the lane picks the
accent colour for the generated featured image and (later) the theme's card
edge and end-of-post CTA.
"""

LANE_CATEGORIES = {
    "consulting": ["Contact Center", "Convoso", "DNC & Compliance", "Dialer Ops", "Sheets Automation"],
    "building": ["Dev Notes", "Games", "Agents & Automation", "Sessions"],
}

# Lowercased category name -> lane, built once at import.
_CATEGORY_TO_LANE = {
    name.lower(): lane
    for lane, names in LANE_CATEGORIES.items()
    for name in names
}


def lane_for(categories: list[str]) -> str | None:
    """
    First category in `categories` that matches a lane (case-insensitive exact
    match against LANE_CATEGORIES) wins. Returns "consulting", "building", or
    None if nothing matches. `categories` are the plain-string category names
    as stored on a draft (see blog_engine/core/draft_manager.py), not WP IDs.
    """
    for category in categories or []:
        lane = _CATEGORY_TO_LANE.get(str(category).strip().lower())
        if lane:
            return lane
    return None

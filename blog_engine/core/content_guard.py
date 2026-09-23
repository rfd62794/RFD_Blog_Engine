"""
blog_engine/core/content_guard.py

Pre-push content checks for rfd-blog-engine.

check(draft) returns a list of reasons the draft must not be pushed to
WordPress; an empty list means the draft is clean. The publisher refuses
to push when this returns anything.
"""

import re

# [ROBERT: ...] placeholders carry facts only Robert can fill in —
# a draft containing one must never leave the engine.
_ROBERT_PLACEHOLDER = re.compile(r"\[ROBERT:[^\]]*\]", re.IGNORECASE)

# Markers that mean the draft is unfinished.
_UNFINISHED_MARKERS = [
    (re.compile(r"\[TODO", re.IGNORECASE), "[TODO"),
    (re.compile(r"\bTBD\b", re.IGNORECASE), "TBD"),
    (re.compile(r"lorem ipsum", re.IGNORECASE), "lorem ipsum"),
]

_CHECKED_FIELDS = ("title", "content", "excerpt")


def check(draft: dict) -> list[str]:
    """
    Check a draft dict for content that must not go to WordPress.

    Flags:
    - any [ROBERT: ...] placeholder (case-insensitive) in title, content or excerpt
    - [TODO, TBD, or lorem ipsum in title, content or excerpt
    - an empty excerpt (the meta description)
    - no categories

    Returns a list of human-readable reasons, one per problem found.
    An empty list means the draft is clean.
    """
    reasons = []

    for field in _CHECKED_FIELDS:
        text = draft.get(field) or ""
        for match in _ROBERT_PLACEHOLDER.finditer(text):
            reasons.append(f"placeholder '{match.group(0)}' in {field}")
        for pattern, label in _UNFINISHED_MARKERS:
            if pattern.search(text):
                reasons.append(f"unfinished marker '{label}' in {field}")

    if not (draft.get("excerpt") or "").strip():
        reasons.append("excerpt is empty (meta description)")

    if not draft.get("categories"):
        reasons.append("no categories assigned")

    return reasons

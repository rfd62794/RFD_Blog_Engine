"""
tests/test_content_guard.py

Unit tests for blog_engine/core/content_guard.py — the pre-push check that
keeps placeholders and unfinished drafts from reaching WordPress.
"""

from blog_engine.core import content_guard


def _clean_draft(**overrides) -> dict:
    draft = {
        "post_id": "test-post",
        "title": "A clean title",
        "content": "Clean content with no placeholders.",
        "excerpt": "A real meta description.",
        "categories": [1],
    }
    draft.update(overrides)
    return draft


def test_clean_draft_returns_empty_list():
    assert content_guard.check(_clean_draft()) == []


def test_robert_placeholder_in_content_flagged():
    reasons = content_guard.check(_clean_draft(content="Revenue: [ROBERT: fill me]"))
    assert any("[ROBERT: fill me]" in r for r in reasons)
    assert any("content" in r for r in reasons)


def test_robert_placeholder_case_insensitive():
    reasons = content_guard.check(_clean_draft(title="[robert: tbd number] post"))
    assert any("placeholder" in r for r in reasons)


def test_robert_placeholder_in_excerpt_flagged():
    reasons = content_guard.check(_clean_draft(excerpt="See [ROBERT: url]"))
    assert any("excerpt" in r for r in reasons)


def test_todo_marker_flagged():
    reasons = content_guard.check(_clean_draft(content="Section one. [TODO finish this]"))
    assert any("[TODO" in r for r in reasons)


def test_tbd_flagged():
    reasons = content_guard.check(_clean_draft(content="The launch date is TBD."))
    assert any("TBD" in r for r in reasons)


def test_lorem_ipsum_flagged():
    reasons = content_guard.check(_clean_draft(content="Lorem ipsum dolor sit amet."))
    assert any("lorem ipsum" in r for r in reasons)


def test_empty_excerpt_flagged():
    assert any("excerpt" in r for r in content_guard.check(_clean_draft(excerpt="")))
    assert any("excerpt" in r for r in content_guard.check(_clean_draft(excerpt="   ")))


def test_no_categories_flagged():
    assert any("categories" in r for r in content_guard.check(_clean_draft(categories=[])))
    assert any("categories" in r for r in content_guard.check(_clean_draft(categories=None)))


def test_multiple_problems_each_get_a_reason():
    reasons = content_guard.check(_clean_draft(
        content="[ROBERT: fill me] and TBD",
        excerpt="",
        categories=[],
    ))
    assert len(reasons) >= 4

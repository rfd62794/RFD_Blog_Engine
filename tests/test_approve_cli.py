"""
tests/test_approve_cli.py

Directive: approve CLI + end-to-end publish-gate proof.
`rfd-blog-engine approve <post_id>` is Robert's approval surface, and a
freshly generated (unapproved) draft can never reach WordPress.
"""

import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from click.testing import CliRunner

from blog_engine.api.devto import DevToHandler
from blog_engine.api.wordpress import WordPressHandler
from blog_engine.cli import cli
from blog_engine.core.draft_manager import DraftManager
from blog_engine.core.inventory import InventoryManager
from blog_engine.core.publisher import Publisher


@pytest.fixture
def drafts_dir(temp_dir):
    return temp_dir / "drafts"


@pytest.fixture
def draft_manager(db, drafts_dir):
    return DraftManager(db, drafts_dir)


@pytest.fixture
def inventory(temp_dir):
    inv_dir = temp_dir / "inventory"
    inv_dir.mkdir(parents=True, exist_ok=True)
    return InventoryManager(inventory_dir=inv_dir)


@pytest.fixture
def wp_handler():
    handler = Mock(spec=WordPressHandler)
    handler.create_post = AsyncMock(return_value={
        "wp_post_id": 123,
        "wp_url": "https://blog.example.com/loop-post"
    })
    handler.upload_media = AsyncMock(return_value=77)
    handler.get_post = AsyncMock(return_value={
        "id": 123,
        "status": "publish",
        "link": "https://blog.example.com/loop-post"
    })
    return handler


@pytest.fixture
def devto_handler():
    handler = Mock(spec=DevToHandler)
    handler.create_article = AsyncMock(return_value={
        "devto_id": 456,
        "devto_url": "https://dev.to/user/loop-post"
    })
    handler.update_article = AsyncMock(return_value={
        "devto_id": 456,
        "devto_url": "https://dev.to/user/loop-post"
    })
    return handler


@pytest.fixture
def publisher(db, draft_manager, inventory, wp_handler, devto_handler):
    return Publisher(db, draft_manager, inventory, wp_handler, devto_handler)


@pytest.fixture
def runner():
    return CliRunner()


def _make_draft(draft_manager, post_id="loop-post", **overrides):
    """Create a draft through the real DraftManager path — status stays 'draft'."""
    kwargs = {
        "post_id": post_id,
        "title": "Loop Post",
        "content": "Real content",
        "excerpt": "Real excerpt",
        "tags": ["one", "two", "three"],
        "categories": ["devlog"],
    }
    kwargs.update(overrides)
    return draft_manager.create_draft(**kwargs)


def _invoke_approve(runner, db, draft_manager, post_id):
    """Run `approve <post_id>` with the CLI's DBManager/DraftManager bound to fixtures."""
    with patch("blog_engine.infra.db_manager.DBManager", return_value=db), \
         patch("blog_engine.core.draft_manager.DraftManager", return_value=draft_manager):
        return runner.invoke(cli, ["approve", post_id])


# --- publish gate: the whole daily-loop path cannot reach WordPress unapproved

def test_unapproved_draft_never_reaches_wordpress(publisher, draft_manager, wp_handler):
    """A freshly created draft (status 'draft', never approved) raises on
    publish_wordpress and the WordPress handler is never called at all."""
    _make_draft(draft_manager)

    with pytest.raises(ValueError) as exc:
        asyncio.run(publisher.publish_wordpress("loop-post"))

    assert "must be approved before publishing" in str(exc.value)
    assert "loop-post" in str(exc.value)
    wp_handler.create_post.assert_not_called()
    wp_handler.upload_media.assert_not_called()
    wp_handler.get_post.assert_not_called()


def test_approved_draft_with_placeholder_still_refused(publisher, draft_manager, wp_handler):
    """Approve via the real approve_draft, then publish: a [ROBERT: ...]
    placeholder still refuses. Approval alone never bypasses content_guard."""
    _make_draft(draft_manager, content="Numbers only Robert has: [ROBERT: fill me]")
    draft_manager.approve_draft("loop-post", approved_by="robert")

    with pytest.raises(ValueError) as exc:
        asyncio.run(publisher.publish_wordpress("loop-post"))

    assert "[ROBERT: fill me]" in str(exc.value)
    wp_handler.create_post.assert_not_called()
    wp_handler.upload_media.assert_not_called()


# --- approve CLI -------------------------------------------------------------

def test_approve_cli_flips_status(runner, db, draft_manager, drafts_dir):
    """`approve <post_id>` flips the draft to approved and echoes the result."""
    _make_draft(draft_manager, post_id="cli-post")

    result = _invoke_approve(runner, db, draft_manager, "cli-post")

    assert result.exit_code == 0
    assert "approved" in result.output

    draft = json.loads((drafts_dir / "cli-post.json").read_text())
    assert draft["status"] == "approved"
    assert draft["approved_by"] == "robert"
    assert draft["approved_at"] is not None


def test_approve_cli_unknown_post_id(runner, db, draft_manager):
    """Unknown post_id exits non-zero with a readable message, no traceback."""
    result = _invoke_approve(runner, db, draft_manager, "no-such-post")

    assert result.exit_code != 0
    assert "Draft not found" in result.output
    assert "Traceback" not in result.output


def test_approve_cli_already_approved(runner, db, draft_manager):
    """Approving an already-approved draft is a clean UsageError, not a crash."""
    _make_draft(draft_manager, post_id="cli-post")

    first = _invoke_approve(runner, db, draft_manager, "cli-post")
    assert first.exit_code == 0

    second = _invoke_approve(runner, db, draft_manager, "cli-post")
    assert second.exit_code != 0
    assert "Cannot approve draft with status: approved" in second.output
    assert "Traceback" not in second.output

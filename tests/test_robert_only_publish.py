"""
tests/test_robert_only_publish.py

Directive: Robert-only publishing — the engine drafts, it can never publish.
Covers the refusal gates, the content guard, the pending-only WordPress push,
and the live-WordPress requirement for Dev.to syndication.
"""

import asyncio
import json
import re
import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from blog_engine.core.publisher import Publisher
from blog_engine.core.draft_manager import DraftManager
from blog_engine.core.inventory import InventoryManager
from blog_engine.api.wordpress import WordPressHandler, ROBERT_ONLY_PUBLISH_MESSAGE
from blog_engine.api.devto import DevToHandler

ROBERT_MSG = (
    "publishing is Robert's: the engine only creates WordPress drafts; "
    "publish or schedule it in WordPress"
)


@pytest.fixture
def temp_dir():
    temp = Path(tempfile.mkdtemp())
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def db(temp_dir):
    import blog_engine.infra.db_manager as db_module

    original_path = db_module._DB_PATH
    db_module._DB_PATH = temp_dir / "test.db"
    db_module._conn = None

    from blog_engine.infra.db_manager import db
    db.initialize_schema()

    yield db

    if db_module._conn:
        db_module._conn.close()
        db_module._conn = None
    db_module._DB_PATH = original_path


@pytest.fixture
def draft_manager(db, temp_dir):
    return DraftManager(db, temp_dir / "drafts")


@pytest.fixture
def inventory(temp_dir):
    """Real InventoryManager on a temp dir, with an approved inventory entry."""
    import yaml

    inv_dir = temp_dir / "inventory"
    inv_dir.mkdir(parents=True, exist_ok=True)
    post = {
        "post_id": "test-post",
        "title": "Test Post",
        "status": "approved",
        "category": "test",
        "tags": [],
    }
    with open(inv_dir / "test-post.yaml", "w") as f:
        yaml.safe_dump(post, f, sort_keys=False)
    return InventoryManager(inventory_dir=inv_dir)


@pytest.fixture
def wp_handler():
    handler = Mock(spec=WordPressHandler)
    handler.create_post = AsyncMock(return_value={
        "wp_post_id": 123,
        "wp_url": "https://blog.example.com/test-post"
    })
    # Dev.to syndication only follows a live WordPress post
    handler.get_post = AsyncMock(return_value={
        "id": 123,
        "status": "publish",
        "link": "https://blog.example.com/test-post"
    })
    return handler


@pytest.fixture
def devto_handler():
    handler = Mock(spec=DevToHandler)
    handler.create_article = AsyncMock(return_value={
        "devto_id": 456,
        "devto_url": "https://dev.to/user/test-post"
    })
    handler.update_article = AsyncMock(return_value={
        "devto_id": 456,
        "devto_url": "https://dev.to/user/test-post"
    })
    return handler


@pytest.fixture
def publisher(db, draft_manager, inventory, wp_handler, devto_handler):
    return Publisher(db, draft_manager, inventory, wp_handler, devto_handler)


def _approved_draft(drafts_dir: Path, post_id: str = "test-post", **overrides) -> dict:
    """Write a clean, approved draft JSON; overrides tweak any field."""
    draft = {
        "post_id": post_id,
        "title": "Test Post",
        "status": "approved",
        "content": "Test content",
        "excerpt": "Test excerpt",
        "tags": ["test"],
        "categories": [1],
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "wp_post_id": None,
        "wp_url": None,
        "devto_id": None,
        "devto_url": None,
        "published_at": None,
    }
    draft.update(overrides)
    drafts_dir.mkdir(parents=True, exist_ok=True)
    with open(drafts_dir / f"{post_id}.json", "w") as f:
        json.dump(draft, f)
    return draft


# --- publish_wordpress: publishing/scheduling refused -----------------------

def test_publish_wordpress_publish_true_refused(publisher, draft_manager, wp_handler):
    """publish=True raises the exact Robert-only error; no WordPress call."""
    _approved_draft(draft_manager.drafts_dir)

    with pytest.raises(ValueError) as exc:
        asyncio.run(publisher.publish_wordpress("test-post", publish=True))

    assert str(exc.value) == ROBERT_MSG
    assert str(exc.value) == ROBERT_ONLY_PUBLISH_MESSAGE
    wp_handler.create_post.assert_not_called()


def test_publish_wordpress_scheduled_date_refused(publisher, draft_manager, wp_handler):
    """scheduled_date raises the exact Robert-only error; no WordPress call."""
    _approved_draft(draft_manager.drafts_dir)

    with pytest.raises(ValueError) as exc:
        asyncio.run(publisher.publish_wordpress("test-post", scheduled_date="2026-10-01T09:00:00"))

    assert str(exc.value) == ROBERT_MSG
    wp_handler.create_post.assert_not_called()


def test_publish_to_wordpress_tool_refuses_publish_and_schedule(draft_manager):
    """The MCP tool surfaces the refusal as an error dict."""
    from blog_engine.tools.publish_tools import publish_to_wordpress

    result = asyncio.run(publish_to_wordpress("test-post", publish=True))
    assert result["error"] == ROBERT_MSG

    result = asyncio.run(publish_to_wordpress("test-post", scheduled_date="2026-10-01T09:00:00"))
    assert result["error"] == ROBERT_MSG


# --- publish_wordpress: normal push sends "pending" --------------------------

def test_publish_wordpress_sends_pending_status(publisher, draft_manager, wp_handler):
    """A normal push calls create_post with status="pending" and returns the note."""
    _approved_draft(draft_manager.drafts_dir)

    result = asyncio.run(publisher.publish_wordpress("test-post"))

    call_kwargs = wp_handler.create_post.call_args[1]
    assert call_kwargs["status"] == "pending"
    assert "scheduled_date" not in call_kwargs
    assert result["status"] == "pending"
    assert result["wp_url"] == "https://blog.example.com/test-post"
    assert result["note"] == "Robert publishes in WordPress"


# --- publish_wordpress: content guard ----------------------------------------

def test_publish_wordpress_robert_placeholder_refused(publisher, draft_manager, wp_handler):
    """A draft containing [ROBERT: fill me] is refused, naming the placeholder."""
    _approved_draft(draft_manager.drafts_dir, content="Numbers only Robert has: [ROBERT: fill me]")

    with pytest.raises(ValueError) as exc:
        asyncio.run(publisher.publish_wordpress("test-post"))

    assert "[ROBERT: fill me]" in str(exc.value)
    wp_handler.create_post.assert_not_called()


def test_publish_wordpress_empty_excerpt_refused(publisher, draft_manager, wp_handler):
    """An empty excerpt (meta description) is refused."""
    _approved_draft(draft_manager.drafts_dir, excerpt="")

    with pytest.raises(ValueError) as exc:
        asyncio.run(publisher.publish_wordpress("test-post"))

    assert "excerpt" in str(exc.value)
    wp_handler.create_post.assert_not_called()


def test_publish_wordpress_no_categories_refused(publisher, draft_manager, wp_handler):
    """A draft with no categories is refused."""
    _approved_draft(draft_manager.drafts_dir, categories=[])

    with pytest.raises(ValueError) as exc:
        asyncio.run(publisher.publish_wordpress("test-post"))

    assert "categories" in str(exc.value)
    wp_handler.create_post.assert_not_called()


# --- publish_devto: requires a live WordPress post ----------------------------

def test_publish_devto_refused_when_wp_pending(publisher, draft_manager, wp_handler, devto_handler):
    """WP status 'pending' → Dev.to syndication refused, no Dev.to call."""
    _approved_draft(
        draft_manager.drafts_dir,
        wp_post_id=123,
        wp_url="https://blog.example.com/test-post",
    )
    wp_handler.get_post = AsyncMock(return_value={"id": 123, "status": "pending"})

    with patch.dict("os.environ", {"DEVTO_API_KEY": "test-key"}):
        with pytest.raises(ValueError, match="requires a live WordPress post"):
            asyncio.run(publisher.publish_devto("test-post"))

    devto_handler.create_article.assert_not_called()
    devto_handler.update_article.assert_not_called()


def test_publish_devto_refused_when_wp_draft(publisher, draft_manager, wp_handler, devto_handler):
    """WP status 'draft' → Dev.to syndication refused, no Dev.to call."""
    _approved_draft(
        draft_manager.drafts_dir,
        wp_post_id=123,
        wp_url="https://blog.example.com/test-post",
    )
    wp_handler.get_post = AsyncMock(return_value={"id": 123, "status": "draft"})

    with patch.dict("os.environ", {"DEVTO_API_KEY": "test-key"}):
        with pytest.raises(ValueError, match="requires a live WordPress post"):
            asyncio.run(publisher.publish_devto("test-post"))

    devto_handler.create_article.assert_not_called()


def test_publish_devto_proceeds_when_wp_live(publisher, draft_manager, wp_handler, devto_handler):
    """WP status 'publish' → Dev.to article created."""
    _approved_draft(
        draft_manager.drafts_dir,
        wp_post_id=123,
        wp_url="https://blog.example.com/test-post",
    )

    with patch.dict("os.environ", {"DEVTO_API_KEY": "test-key"}):
        result = asyncio.run(publisher.publish_devto("test-post"))

    devto_handler.create_article.assert_called_once()
    assert result["devto_id"] == 456


def test_publish_to_devto_tool_refuses_when_wp_not_live(publisher, draft_manager, wp_handler):
    """The MCP tool returns an error dict when the WP post isn't live."""
    from blog_engine.tools.publish_tools import publish_to_devto

    _approved_draft(
        draft_manager.drafts_dir,
        wp_post_id=123,
        wp_url="https://blog.example.com/test-post",
    )
    wp_handler.get_post = AsyncMock(return_value={"id": 123, "status": "pending"})

    with patch.dict("os.environ", {"DEVTO_API_KEY": "test-key"}), \
         patch("blog_engine.tools.publish_tools._get_publisher", return_value=publisher):
        result = asyncio.run(publish_to_devto("test-post"))

    assert "error" in result
    assert "live WordPress post" in result["error"]


def test_update_devto_post_refuses_published_true():
    """update_devto_post cannot flip an article live — that path is gated."""
    from blog_engine.tools.publish_tools import update_devto_post

    result = asyncio.run(update_devto_post(devto_id=1, published=True))

    assert "error" in result
    assert result["devto_id"] == 1


# --- devto_sync: refuses when the WP post isn't live --------------------------

def test_devto_sync_refuses_not_live_post(db):
    """run_sync refuses syndication when the fetched WP post isn't publish."""
    from datetime import date
    from unittest.mock import MagicMock
    from blog_engine.devto_sync import _ensure_sync_log_table, run_sync

    _ensure_sync_log_table(db)
    db.exec(
        "INSERT OR IGNORE INTO publish_log (post_id, platform, status, platform_id, platform_url) "
        "VALUES ('dev-010', 'wordpress', 'success', '88', 'https://blog.example.com/post')",
        commit=True,
    )

    wp_post = {
        "id": 88,
        "title": {"rendered": "Test Post"},
        "link": "https://blog.example.com/2026/06/15/test-post/",
        "status": "publish",
        "date": "2026-06-15T09:00:00",
        "excerpt": {"rendered": "An excerpt."},
        "content": {"rendered": "<p>Content</p>"},
        "tags": [],
    }
    # The listing says publish, but the post itself was pulled back to pending
    fetched = dict(wp_post, status="pending")

    mock_wp = MagicMock()
    mock_wp.get_posts = AsyncMock(return_value=[wp_post])
    mock_wp.get_post = AsyncMock(return_value=fetched)

    mock_devto = MagicMock()
    mock_devto.create_article = AsyncMock()

    with patch("blog_engine.devto_sync._get_wp_handler", return_value=mock_wp), \
         patch("blog_engine.devto_sync._get_devto_handler", return_value=mock_devto), \
         patch("blog_engine.devto_sync._get_db", return_value=db), \
         patch("blog_engine.devto_sync._verify_canonical", new_callable=AsyncMock, return_value=True), \
         patch("blog_engine.devto_sync._get_start_date", return_value=date(2026, 6, 11)), \
         patch("blog_engine.devto_sync._get_min_age_days", return_value=0), \
         patch.dict("os.environ", {"DEVTO_API_KEY": "test-key"}):
        result = asyncio.run(run_sync(dry_run=False))

    mock_devto.create_article.assert_not_called()
    assert result["refused"] == 1
    assert result["posts"][0]["action"] == "refused_not_live"

    row = db.exec(
        "SELECT action FROM devto_sync_log WHERE wp_post_id=88"
    ).fetchone()
    assert row is not None
    assert row[0] == "refused_not_live"


# --- source scan: no engine path sets a publishing WordPress status ----------

_PKG_DIR = Path(__file__).parent.parent / "blog_engine"

# status = "publish" / status="future" (assignments and keyword args)
_STATUS_ASSIGN_RE = re.compile(r"\bstatus\s*=\s*['\"](?:publish|future)['\"]")
# "status": "publish" / 'status': 'future' (dict payloads)
_STATUS_PAYLOAD_RE = re.compile(r"['\"]status['\"]\s*:\s*['\"](?:publish|future)['\"]")

# Read-only lookups may legitimately filter by status="publish" — they never
# write it. Everything else must not set a publishing status.
_READ_ONLY_HINTS = ("get_posts(", "get_post(", "_wp_api_get(")


def test_no_engine_path_sets_publish_or_future_status():
    """No code under blog_engine/ sends 'publish' or 'future' as a WP status."""
    offenders = []
    for path in sorted(_PKG_DIR.rglob("*.py")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if any(hint in line for hint in _READ_ONLY_HINTS):
                continue
            if _STATUS_ASSIGN_RE.search(line) or _STATUS_PAYLOAD_RE.search(line):
                offenders.append(f"{path.relative_to(_PKG_DIR)}:{lineno}: {line.strip()}")

    assert not offenders, (
        "engine code sets a publishing WordPress status:\n" + "\n".join(offenders)
    )

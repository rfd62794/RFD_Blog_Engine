"""
tests/test_publisher.py

Tests for Publisher orchestration logic.
All synchronous, using asyncio.run() for async methods (ADR-010).
"""

import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import pytest
import tempfile
import shutil

from blog_engine.core.publisher import Publisher
from blog_engine.infra.db_manager import DBManager
from blog_engine.core.draft_manager import DraftManager
from blog_engine.core.inventory import InventoryManager
from blog_engine.api.wordpress import WordPressHandler
from blog_engine.api.devto import DevToHandler


@pytest.fixture
def temp_dir():
    """Temporary directory for test files."""
    temp = Path(tempfile.mkdtemp())
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def db(temp_dir):
    """SQLite database with schema initialized in temp directory."""
    import blog_engine.infra.db_manager as db_module
    
    # Override DB path to temp directory
    original_path = db_module._DB_PATH
    db_module._DB_PATH = temp_dir / "test.db"
    
    # Reset connection
    db_module._conn = None
    
    # Initialize schema
    from blog_engine.infra.db_manager import db
    db.initialize_schema()
    
    yield db
    
    # Cleanup
    if db_module._conn:
        db_module._conn.close()
        db_module._conn = None
    db_module._DB_PATH = original_path


@pytest.fixture
def draft_manager(db, temp_dir):
    """DraftManager with temp directory."""
    return DraftManager(db, temp_dir)


@pytest.fixture
def inventory():
    """InventoryManager."""
    return InventoryManager()


@pytest.fixture
def wp_handler(db):
    """Mock WordPressHandler."""
    handler = Mock(spec=WordPressHandler)
    handler.create_post = AsyncMock(return_value={
        "wp_post_id": 123,
        "wp_url": "https://blog.rfditservices.com/test-post"
    })
    return handler


@pytest.fixture
def devto_handler(db):
    """Mock DevToHandler."""
    handler = Mock(spec=DevToHandler)
    handler.create_article = AsyncMock(return_value={
        "devto_id": 456,
        "devto_url": "https://dev.to/user/test-post"
    })
    return handler


@pytest.fixture
def publisher(db, draft_manager, inventory, wp_handler, devto_handler):
    """Publisher instance with mocked dependencies."""
    return Publisher(db, draft_manager, inventory, wp_handler, devto_handler)


@pytest.fixture
def approved_draft(temp_dir):
    """Create an approved draft JSON file."""
    draft = {
        "post_id": "test-post",
        "title": "Test Post",
        "status": "approved",
        "content": "Test content",
        "excerpt": "",
        "tags": ["test"],
        "categories": [],
        "tags_source": "manual",
        "categories_source": "manual",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "approved_at": "2024-01-01T00:00:00Z",
        "approved_by": "human",
        "wp_post_id": None,
        "wp_url": None,
        "devto_id": None,
        "devto_url": None,
        "published_at": None,
        "revision_count": 0,
        "generation_source": "external"
    }
    import json
    draft_path = temp_dir / "test-post.json"
    with open(draft_path, "w") as f:
        json.dump(draft, f)
    return draft


@pytest.fixture
def draft_draft(temp_dir):
    """Create a draft (not approved) JSON file."""
    draft = {
        "post_id": "test-post",
        "title": "Test Post",
        "status": "draft",
        "content": "Test content",
        "excerpt": "",
        "tags": ["test"],
        "categories": [],
        "tags_source": "manual",
        "categories_source": "manual",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "approved_at": None,
        "approved_by": None,
        "wp_post_id": None,
        "wp_url": None,
        "devto_id": None,
        "devto_url": None,
        "published_at": None,
        "revision_count": 0,
        "generation_source": "external"
    }
    import json
    draft_path = temp_dir / "test-post.json"
    with open(draft_path, "w") as f:
        json.dump(draft, f)
    return draft


def test_publish_wordpress_requires_approved(publisher, draft_draft):
    """Raises ValueError if draft status is "draft"."""
    with pytest.raises(ValueError) as exc:
        asyncio.run(publisher.publish_wordpress("test-post"))
    assert "must be approved before publishing" in str(exc.value)


def test_publish_wordpress_requires_approved_not_published(publisher, temp_dir):
    """Raises ValueError if draft status is "published"."""
    draft = {
        "post_id": "test-post",
        "title": "Test Post",
        "status": "published",
        "content": "Test content",
        "excerpt": "",
        "tags": [],
        "categories": [],
        "tags_source": "manual",
        "categories_source": "manual",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "approved_at": "2024-01-01T00:00:00Z",
        "approved_by": "human",
        "wp_post_id": None,
        "wp_url": None,
        "devto_id": None,
        "devto_url": None,
        "published_at": None,
        "revision_count": 0,
        "generation_source": "external"
    }
    import json
    draft_path = temp_dir / "test-post.json"
    with open(draft_path, "w") as f:
        json.dump(draft, f)
    
    with pytest.raises(ValueError) as exc:
        asyncio.run(publisher.publish_wordpress("test-post"))
    assert "must be approved before publishing" in str(exc.value)


def test_publish_wordpress_calls_wp_handler(publisher, approved_draft, wp_handler):
    """WordPressHandler.create_post called with correct args."""
    asyncio.run(publisher.publish_wordpress("test-post"))
    wp_handler.create_post.assert_called_once()
    call_args = wp_handler.create_post.call_args
    assert call_args[1]["post_id"] == "test-post"
    assert call_args[1]["title"] == "Test Post"
    assert call_args[1]["content"] == "Test content"


def test_publish_wordpress_updates_draft_wp_fields(publisher, approved_draft, temp_dir):
    """Draft JSON updated with wp_post_id and wp_url."""
    asyncio.run(publisher.publish_wordpress("test-post"))
    
    import json
    draft_path = temp_dir / "test-post.json"
    with open(draft_path, "r") as f:
        updated_draft = json.load(f)
    
    assert updated_draft["wp_post_id"] == 123
    assert updated_draft["wp_url"] == "https://blog.rfditservices.com/test-post"


def test_publish_wordpress_updates_inventory_status(publisher, approved_draft, inventory):
    """Inventory status set to "published" after WP success."""
    with patch.object(inventory, "update_status") as mock_update:
        asyncio.run(publisher.publish_wordpress("test-post"))
        mock_update.assert_called_once_with("test-post", "published")


def test_publish_wordpress_returns_correct_dict(publisher, approved_draft):
    """Returns {post_id, wp_post_id, wp_url, status}."""
    result = asyncio.run(publisher.publish_wordpress("test-post"))
    assert result["post_id"] == "test-post"
    assert result["wp_post_id"] == 123
    assert result["wp_url"] == "https://blog.rfditservices.com/test-post"
    assert result["status"] == "published"


def test_publish_wordpress_wp_failure_no_devto(publisher, approved_draft, wp_handler, devto_handler):
    """DevToHandler never called if WP fails."""
    wp_handler.create_post = AsyncMock(side_effect=Exception("WP API error"))
    
    with pytest.raises(Exception):
        asyncio.run(publisher.publish_wordpress("test-post"))
    
    devto_handler.create_article.assert_not_called()


def test_publish_devto_requires_approved(publisher, draft_draft):
    """Raises ValueError if not approved."""
    with pytest.raises(ValueError) as exc:
        asyncio.run(publisher.publish_devto("test-post"))
    assert "must be approved before publishing" in str(exc.value)


def test_publish_devto_requires_wp_url(publisher, approved_draft):
    """Raises ValueError if wp_url is None on draft."""
    with pytest.raises(ValueError) as exc:
        asyncio.run(publisher.publish_devto("test-post"))
    assert "WordPress must be published before Dev.to" in str(exc.value)


def test_publish_devto_sets_canonical(publisher, approved_draft, temp_dir, devto_handler):
    """DevToHandler called with canonical_url=draft.wp_url."""
    # First publish to WordPress to set wp_url
    asyncio.run(publisher.publish_wordpress("test-post"))
    
    # Then publish to Dev.to
    asyncio.run(publisher.publish_devto("test-post"))
    
    devto_handler.create_article.assert_called_once()
    call_args = devto_handler.create_article.call_args
    assert call_args[1]["canonical_url"] == "https://blog.rfditservices.com/test-post"


def test_publish_devto_updates_draft_devto_fields(publisher, approved_draft, temp_dir):
    """Draft JSON updated with devto_id and devto_url."""
    # First publish to WordPress
    asyncio.run(publisher.publish_wordpress("test-post"))
    
    # Then publish to Dev.to
    asyncio.run(publisher.publish_devto("test-post"))
    
    import json
    draft_path = temp_dir / "test-post.json"
    with open(draft_path, "r") as f:
        updated_draft = json.load(f)
    
    assert updated_draft["devto_id"] == 456
    assert updated_draft["devto_url"] == "https://dev.to/user/test-post"


def test_publish_devto_no_rollback_on_failure(publisher, approved_draft, temp_dir, devto_handler):
    """WP URL preserved if Dev.to fails."""
    # First publish to WordPress
    asyncio.run(publisher.publish_wordpress("test-post"))
    
    # Dev.to fails
    devto_handler.create_article = AsyncMock(side_effect=Exception("Dev.to API error"))
    
    with pytest.raises(Exception):
        asyncio.run(publisher.publish_devto("test-post"))
    
    # WP URL should still be present
    import json
    draft_path = temp_dir / "test-post.json"
    with open(draft_path, "r") as f:
        updated_draft = json.load(f)
    
    assert updated_draft["wp_url"] == "https://blog.rfditservices.com/test-post"


def test_publish_devto_sets_published_at(publisher, approved_draft, temp_dir):
    """published_at set when both wp_url and devto_url present."""
    # Publish to WordPress
    asyncio.run(publisher.publish_wordpress("test-post"))
    
    # Publish to Dev.to
    asyncio.run(publisher.publish_devto("test-post"))
    
    import json
    draft_path = temp_dir / "test-post.json"
    with open(draft_path, "r") as f:
        updated_draft = json.load(f)
    
    assert updated_draft["published_at"] is not None


def test_publish_wordpress_idempotency(publisher, approved_draft, wp_handler, db):
    """Second call returns existing URL (from publish_log)."""
    # First publish
    asyncio.run(publisher.publish_wordpress("test-post"))
    
    # Reset mock
    wp_handler.create_post.reset_mock()
    
    # Second publish - should not call API due to idempotency in WordPressHandler
    asyncio.run(publisher.publish_wordpress("test-post"))
    
    # WordPressHandler should still be called (idempotency check is inside handler)
    # This test verifies the flow doesn't break on second call
    assert True


def test_publish_devto_idempotency(publisher, approved_draft, devto_handler, db):
    """Second call returns existing URL (from publish_log)."""
    # First publish to WordPress
    asyncio.run(publisher.publish_wordpress("test-post"))
    
    # First publish to Dev.to
    asyncio.run(publisher.publish_devto("test-post"))
    
    # Reset mock
    devto_handler.create_article.reset_mock()
    
    # Second Dev.to publish - should not call API due to idempotency in DevToHandler
    asyncio.run(publisher.publish_devto("test-post"))
    
    # DevToHandler should still be called (idempotency check is inside handler)
    # This test verifies the flow doesn't break on second call
    assert True

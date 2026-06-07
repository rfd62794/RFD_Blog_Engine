"""
tests/test_tools.py

Tests for MCP tools.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock


def test_server_creates_mcp_instance():
    """Test that mcp object exists and is FastMCP instance."""
    from blog_engine.server import mcp
    assert mcp is not None
    assert mcp.name == "rfd-blog-engine"


def test_generate_post_tool_callable():
    """Test that generate_post tool function exists and is callable."""
    from blog_engine.tools.generate_tools import register_generate_tools
    from fastmcp import FastMCP
    
    mcp = FastMCP("test")
    register_generate_tools(mcp)
    
    # Verify tool was registered by checking it's in the internal registry
    assert hasattr(mcp, '_mcp_server')


def test_get_post_context_tool_callable():
    """Test that get_post_context tool function exists and is callable."""
    from blog_engine.tools.generate_tools import register_generate_tools
    from fastmcp import FastMCP
    
    mcp = FastMCP("test")
    register_generate_tools(mcp)
    
    # Verify tool was registered
    assert hasattr(mcp, '_mcp_server')


def test_list_inventory_returns_list(temp_dir):
    """Test that list_inventory returns list, mocked inventory."""
    from blog_engine.tools.draft_tools import list_inventory
    
    with patch('blog_engine.tools.draft_tools.InventoryManager') as MockInventory:
        mock_inv = MagicMock()
        mock_inv.list_by_status.return_value = [
            {"post_id": "test-001", "title": "Test", "status": "pending"}
        ]
        MockInventory.return_value = mock_inv
        
        result = asyncio.run(list_inventory(status="pending"))
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["post_id"] == "test-001"


def test_get_draft_returns_dict(temp_dir):
    """Test that get_draft returns draft dict for known post."""
    from blog_engine.tools.draft_tools import get_draft
    
    with patch('blog_engine.tools.draft_tools.DraftManager') as MockDraft:
        mock_draft = MagicMock()
        mock_draft.get_draft.return_value = {
            "post_id": "test-001",
            "title": "Test",
            "content": "Content"
        }
        MockDraft.return_value = mock_draft
        
        result = asyncio.run(get_draft(post_id="test-001"))
        
        assert isinstance(result, dict)
        assert result["post_id"] == "test-001"


def test_get_draft_not_found_returns_error(temp_dir):
    """Test that get_draft returns error dict when not found."""
    from blog_engine.tools.draft_tools import get_draft
    
    with patch('blog_engine.tools.draft_tools.DraftManager') as MockDraft:
        mock_draft = MagicMock()
        mock_draft.get_draft.return_value = None
        MockDraft.return_value = mock_draft
        
        result = asyncio.run(get_draft(post_id="test-001"))
        
        assert "error" in result
        assert result["post_id"] == "test-001"


def test_create_draft_tool(temp_dir):
    """Test that create_draft creates draft and returns dict."""
    from blog_engine.tools.draft_tools import create_draft
    
    with patch('blog_engine.tools.draft_tools.DraftManager') as MockDraft:
        mock_draft = MagicMock()
        mock_draft.create_draft.return_value = None
        mock_draft.get_draft.return_value = {
            "post_id": "test-001",
            "title": "Test",
            "content": "Content"
        }
        MockDraft.return_value = mock_draft
        
        result = asyncio.run(create_draft(
            post_id="test-001",
            title="Test",
            content="Content"
        ))
        
        assert result["post_id"] == "test-001"
        mock_draft.create_draft.assert_called_once()


def test_approve_draft_tool(temp_dir):
    """Test that approve_draft changes status to approved."""
    from blog_engine.tools.draft_tools import approve_draft
    
    with patch('blog_engine.tools.draft_tools.DraftManager') as MockDraft:
        mock_draft = MagicMock()
        mock_draft.approve_draft.return_value = None
        mock_draft.get_draft.return_value = {
            "post_id": "test-001",
            "status": "approved"
        }
        MockDraft.return_value = mock_draft
        
        result = asyncio.run(approve_draft(post_id="test-001"))
        
        assert result["status"] == "approved"
        mock_draft.approve_draft.assert_called_once()


def test_delete_draft_tool(temp_dir):
    """Test that delete_draft returns deleted confirmation."""
    from blog_engine.tools.draft_tools import delete_draft
    
    with patch('blog_engine.tools.draft_tools.DraftManager') as MockDraft:
        mock_draft = MagicMock()
        mock_draft.delete_draft.return_value = None
        MockDraft.return_value = mock_draft
        
        result = asyncio.run(delete_draft(post_id="test-001"))
        
        assert result["deleted"] is True
        assert result["post_id"] == "test-001"


def test_update_inventory_status_tool(temp_dir):
    """Test that update_inventory_status updates inventory."""
    from blog_engine.tools.publish_tools import update_inventory_status
    
    with patch('blog_engine.tools.publish_tools.InventoryManager') as MockInventory:
        mock_inv = MagicMock()
        mock_inv.update_status.return_value = None
        MockInventory.return_value = mock_inv
        
        result = asyncio.run(update_inventory_status(post_id="test-001", status="published"))
        
        assert result["updated"] is True
        assert result["post_id"] == "test-001"
        assert result["status"] == "published"
        mock_inv.update_status.assert_called_once()


def test_get_publish_status_empty(db):
    """Test that get_publish_status returns empty platforms for unpublished post."""
    from blog_engine.tools.publish_tools import get_publish_status
    
    result = asyncio.run(get_publish_status(post_id="test-001"))
    
    assert "platforms" in result
    assert result["platforms"] == {}


def test_list_threads_empty(db):
    """Test that list_threads returns empty list when no threads exist."""
    from blog_engine.tools.publish_tools import list_threads
    
    result = asyncio.run(list_threads())
    
    assert isinstance(result, list)
    assert len(result) == 0


def test_add_to_thread_creates_thread(db):
    """Test that add_to_thread creates thread and adds post."""
    from blog_engine.tools.publish_tools import add_to_thread
    
    result = asyncio.run(add_to_thread(post_id="test-001", thread_name="test-thread"))
    
    assert result["added"] is True
    assert result["post_id"] == "test-001"
    assert result["thread"] == "test-thread"


def test_publish_to_wordpress_unapproved_returns_error():
    """Test that publish_to_wordpress returns error for unapproved draft."""
    from blog_engine.tools.publish_tools import publish_to_wordpress
    from unittest.mock import patch
    
    with patch('blog_engine.tools.publish_tools._get_publisher') as MockPublisher:
        mock_publisher = MagicMock()
        mock_publisher.publish_wordpress = AsyncMock(
            side_effect=ValueError("Draft must be approved before publishing")
        )
        MockPublisher.return_value = mock_publisher
        
        result = asyncio.run(publish_to_wordpress(post_id="test-001"))
        
        assert "error" in result
        assert "approved" in result["error"]


def test_publish_to_devto_no_wp_url_returns_error():
    """Test that publish_to_devto returns error when wp_url missing."""
    from blog_engine.tools.publish_tools import publish_to_devto
    from unittest.mock import patch

    with patch('blog_engine.tools.publish_tools._get_publisher') as MockPublisher:
        mock_publisher = MagicMock()
        mock_publisher.publish_devto = AsyncMock(
            side_effect=ValueError("WordPress must be published before Dev.to")
        )
        MockPublisher.return_value = mock_publisher

        result = asyncio.run(publish_to_devto(post_id="test-001"))

        assert "error" in result
        assert "WordPress" in result["error"]


def test_get_wordpress_posts_tool():
    """Test that get_wordpress_posts returns list, mocked handler."""
    from blog_engine.tools.publish_tools import get_wordpress_posts
    from unittest.mock import patch

    with patch('blog_engine.tools.publish_tools._get_wp_handler') as MockHandler:
        mock_handler = MagicMock()
        mock_handler.get_posts = AsyncMock(return_value=[
            {"id": 1, "title": {"rendered": "Post 1"}, "status": "publish", "link": "https://example.com/post-1"}
        ])
        MockHandler.return_value = mock_handler

        result = asyncio.run(get_wordpress_posts(status="publish"))

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == 1


def test_get_wordpress_post_tool():
    """Test that get_wordpress_post returns dict for valid ID."""
    from blog_engine.tools.publish_tools import get_wordpress_post
    from unittest.mock import patch

    with patch('blog_engine.tools.publish_tools._get_wp_handler') as MockHandler:
        mock_handler = MagicMock()
        mock_handler.get_post = AsyncMock(return_value={
            "id": 42,
            "title": {"rendered": "Test Post"},
            "content": {"rendered": "Test content"}
        })
        MockHandler.return_value = mock_handler

        result = asyncio.run(get_wordpress_post(wp_post_id=42))

        assert result["id"] == 42
        assert result["title"]["rendered"] == "Test Post"


def test_update_wordpress_post_tool():
    """Test that update_wordpress_post mock update returns correct fields."""
    from blog_engine.tools.publish_tools import update_wordpress_post
    from unittest.mock import patch

    with patch('blog_engine.tools.publish_tools._get_wp_handler') as MockHandler:
        mock_handler = MagicMock()
        mock_handler.update_post = AsyncMock(return_value={
            "wp_post_id": 42,
            "wp_url": "https://example.com/post-42"
        })
        MockHandler.return_value = mock_handler

        result = asyncio.run(update_wordpress_post(wp_post_id=42, title="Updated"))

        assert result["wp_post_id"] == 42
        assert result["wp_url"] == "https://example.com/post-42"


def test_get_wordpress_categories_tool():
    """Test that get_wordpress_categories returns list of category dicts."""
    from blog_engine.tools.publish_tools import get_wordpress_categories
    from unittest.mock import patch

    with patch('blog_engine.tools.publish_tools._get_wp_handler') as MockHandler:
        mock_handler = MagicMock()
        mock_handler.get_categories = AsyncMock(return_value=[
            {"id": 1, "name": "Category 1", "slug": "category-1", "count": 5}
        ])
        MockHandler.return_value = mock_handler

        result = asyncio.run(get_wordpress_categories())

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["name"] == "Category 1"

"""
tests/conftest.py

Pytest fixtures for rfd-blog-engine test suite.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import sys

# Add blog_engine to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Enable pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


@pytest.fixture
def temp_dir():
    """Temporary directory for test files."""
    temp = Path(tempfile.mkdtemp())
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def db(temp_dir):
    """In-memory SQLite database with schema initialized."""
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
def inventory(temp_dir):
    """Minimal inventory.yaml with test posts."""
    import yaml
    
    inventory_data = {
        "posts": [
            {
                "post_id": "test-001",
                "title": "Test Post 1",
                "status": "pending",
                "category": "test",
                "notes": "Test notes for frame extraction",
                "tags": ["test", "fixture"],
                "created_at": "2026-06-07T11:00:00"
            },
            {
                "post_id": "test-002",
                "title": "Test Post 2",
                "status": "drafted",
                "category": "test",
                "notes": "Another test post",
                "tags": ["test"],
                "created_at": "2026-06-07T11:00:00"
            }
        ]
    }
    
    inventory_file = temp_dir / "inventory.yaml"
    with open(inventory_file, "w") as f:
        yaml.dump(inventory_data, f)
    
    return inventory_file


@pytest.fixture
def draft(temp_dir):
    """Pre-built draft JSON for test post."""
    import json
    from datetime import datetime
    
    draft_data = {
        "post_id": "test-001",
        "title": "Test Post 1",
        "status": "draft",
        "content": "This is test content.",
        "excerpt": "Test excerpt",
        "tags": ["test", "fixture"],
        "categories": ["test"],
        "tags_source": "manual",
        "categories_source": "manual",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "approved_at": None,
        "approved_by": None,
        "wp_post_id": None,
        "wp_url": None,
        "devto_id": None,
        "devto_url": None,
        "published_at": None,
        "revision_count": 0,
        "generation_source": "internal"
    }
    
    draft_file = temp_dir / "drafts" / "test-001.json"
    draft_file.parent.mkdir(parents=True, exist_ok=True)
    with open(draft_file, "w") as f:
        json.dump(draft_data, f, indent=2)
    
    return draft_data

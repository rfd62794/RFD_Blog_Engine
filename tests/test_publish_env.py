"""publish_tools loads the repo .env for direct (non-MCP) calls without overriding the real environment."""
import os
from unittest.mock import patch

import pytest

from blog_engine.tools import publish_tools

KEYS = ("WORDPRESS_URL", "WORDPRESS_USER", "WORDPRESS_APP_PASSWORD", "DEVTO_API_KEY")


@pytest.fixture
def clean_env():
    """os.environ without the credential keys; everything is restored afterwards (no leak between tests)."""
    with patch.dict(os.environ, clear=False):
        for k in KEYS:
            os.environ.pop(k, None)
        yield


def test_load_env_fills_missing_values(tmp_path, clean_env):
    env = tmp_path / ".env"
    env.write_text("WORDPRESS_URL=https://example.test\nWORDPRESS_USER=from-file\n", encoding="utf-8")
    os.environ["WORDPRESS_USER"] = "from-environment"
    publish_tools._load_env(env)
    assert os.environ["WORDPRESS_URL"] == "https://example.test"
    assert os.environ["WORDPRESS_USER"] == "from-environment"  # the launcher's value wins


def test_load_env_without_file_is_a_no_op(tmp_path, clean_env):
    publish_tools._load_env(tmp_path / "missing.env")
    assert "WORDPRESS_URL" not in os.environ


def test_factory_reads_credentials_from_env_file(tmp_path, clean_env, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("WORDPRESS_URL=https://example.test\nWORDPRESS_USER=u\nWORDPRESS_APP_PASSWORD=p\n", encoding="utf-8")
    monkeypatch.setattr(publish_tools, "ENV_FILE", env)
    monkeypatch.setattr(publish_tools, "_load_env", lambda env_file=env: publish_tools.load_dotenv(env_file, override=False))
    with patch.object(publish_tools, "DBManager"), patch.object(publish_tools, "WordPressHandler") as wp:
        publish_tools._get_wp_handler()
    assert wp.call_args.args[1:] == ("https://example.test", "u", "p")


def test_factory_without_env_file_still_reports_missing(tmp_path, clean_env, monkeypatch):
    monkeypatch.setattr(publish_tools, "ENV_FILE", tmp_path / "missing.env")
    monkeypatch.setattr(publish_tools, "_load_env", lambda env_file=tmp_path / "missing.env": None)
    with pytest.raises(EnvironmentError, match="WORDPRESS_URL"):
        publish_tools._get_wp_handler()

"""publish_tools loads the repo .env for direct (non-MCP) calls without overriding the real environment."""
import os

from blog_engine.tools import publish_tools


def test_load_env_fills_missing_values(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("WORDPRESS_URL=https://example.test\nWORDPRESS_USER=from-file\n", encoding="utf-8")
    monkeypatch.delenv("WORDPRESS_URL", raising=False)
    monkeypatch.setenv("WORDPRESS_USER", "from-environment")
    publish_tools._load_env(env)
    assert os.environ["WORDPRESS_URL"] == "https://example.test"
    assert os.environ["WORDPRESS_USER"] == "from-environment"  # the launcher's value wins


def test_load_env_without_file_is_a_no_op(tmp_path, monkeypatch):
    monkeypatch.delenv("WORDPRESS_URL", raising=False)
    publish_tools._load_env(tmp_path / "missing.env")
    assert "WORDPRESS_URL" not in os.environ

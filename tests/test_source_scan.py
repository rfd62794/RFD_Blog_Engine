"""
tests/test_source_scan.py

Tests for daily draft source scanning (source_scan.py) and the generate-daily
CLI command. Git history is exercised against real throwaway repos (tmp_path +
git init/commit) rather than mocking subprocess — more honest than mocking git.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from blog_engine.cli import cli
from blog_engine.core.draft_manager import DraftManager
from blog_engine.core.inventory import InventoryManager
from blog_engine.core.source_scan import (
    ALLOWED_REPOS,
    register_candidates,
    scan_recent_activity,
)


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _commit(repo: Path, filename: str, message: str) -> None:
    (repo / filename).write_text(f"content of {filename}\n")
    _git(repo, "add", filename)
    _git(repo, "commit", "-m", message)


@pytest.fixture
def git_repo(tmp_path):
    """Real throwaway git repo (no commits — tests add their own)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")
    return repo


def test_allowed_repos_starts_with_expected_paths():
    assert ALLOWED_REPOS == ["C:/Github/RFD_Blog_Engine", "C:/Github/AgentFlow"]


def test_scan_returns_candidates_most_recent_first(git_repo, monkeypatch):
    _commit(git_repo, "a.txt", "Add first real feature")
    _commit(git_repo, "b.txt", "Fix second real bug")
    monkeypatch.setenv("SOURCE_SCAN_REPOS", str(git_repo))

    candidates = scan_recent_activity(since_days=2)

    assert len(candidates) == 2
    assert candidates[0]["notes"] == "Fix second real bug"
    assert candidates[1]["notes"] == "Add first real feature"

    c = candidates[0]
    assert c["post_id"] == f"src-{_git(git_repo, 'rev-parse', '--short', 'HEAD')}"
    assert c["title"] == "Fix second real bug"
    assert c["category"] == "building"
    assert c["tags"] == []
    assert c["source_repo"] == str(git_repo)
    assert c["source_ref"] == _git(git_repo, "rev-parse", "HEAD")
    assert len(c["source_ref"]) == 40


def test_scan_skips_bookkeeping_subjects(git_repo, monkeypatch):
    _commit(git_repo, "a.txt", "Merge branch 'x'")
    _commit(git_repo, "b.txt", "Queue: dispatch something")
    _commit(git_repo, "c.txt", "Real shipped work")
    monkeypatch.setenv("SOURCE_SCAN_REPOS", str(git_repo))

    candidates = scan_recent_activity(since_days=2)

    assert [c["notes"] for c in candidates] == ["Real shipped work"]


def test_scan_respects_max_candidates(git_repo, monkeypatch):
    for i in range(4):
        _commit(git_repo, f"f{i}.txt", f"Commit number {i}")
    monkeypatch.setenv("SOURCE_SCAN_REPOS", str(git_repo))

    candidates = scan_recent_activity(since_days=2, max_candidates=2)

    assert len(candidates) == 2
    assert candidates[0]["notes"] == "Commit number 3"
    assert candidates[1]["notes"] == "Commit number 2"


def test_scan_returns_empty_on_repo_with_no_commits(git_repo, monkeypatch):
    """git log on a zero-commit repo fails; the scan must skip it, not raise."""
    monkeypatch.setenv("SOURCE_SCAN_REPOS", str(git_repo))
    assert scan_recent_activity(since_days=2) == []


def test_scan_skips_non_git_path(tmp_path, monkeypatch):
    not_repo = tmp_path / "not-a-repo"
    not_repo.mkdir()
    monkeypatch.setenv("SOURCE_SCAN_REPOS", str(not_repo))
    assert scan_recent_activity(since_days=2) == []


def test_scan_never_scans_repo_outside_allow_list(git_repo, monkeypatch):
    """A repo not on the allow-list is skipped even when passed explicitly."""
    _commit(git_repo, "a.txt", "Real work")
    monkeypatch.setenv("SOURCE_SCAN_REPOS", "C:/Github/AgentFlow")

    assert scan_recent_activity(repos=[str(git_repo)], since_days=2) == []


def test_scan_truncates_long_subjects(git_repo, monkeypatch):
    _commit(git_repo, "a.txt", "x" * 120)
    monkeypatch.setenv("SOURCE_SCAN_REPOS", str(git_repo))

    candidates = scan_recent_activity(since_days=2)

    assert len(candidates) == 1
    assert len(candidates[0]["title"]) <= 72
    assert candidates[0]["notes"] == "x" * 120


def test_register_candidates_adds_posts(tmp_path):
    inventory = InventoryManager(tmp_path / "inventory")
    candidates = [
        {
            "post_id": "src-abc1234",
            "title": "Title one",
            "notes": "Subject one",
            "category": "building",
            "tags": [],
            "source_repo": "r",
            "source_ref": "x" * 40,
        },
        {
            "post_id": "src-def5678",
            "title": "Title two",
            "notes": "Subject two",
            "category": "building",
            "tags": [],
            "source_repo": "r",
            "source_ref": "y" * 40,
        },
    ]

    registered = register_candidates(candidates, inventory)

    assert registered == ["src-abc1234", "src-def5678"]
    post = inventory.get_post("src-abc1234")
    assert post["title"] == "Title one"
    assert post["status"] == "pending"
    assert post["notes"] == "Subject one"


def test_register_candidates_idempotent(tmp_path):
    """Running twice registers nothing the second time — safe to run daily."""
    inventory = InventoryManager(tmp_path / "inventory")
    candidates = [
        {
            "post_id": "src-abc1234",
            "title": "Title one",
            "notes": "Subject one",
            "category": "building",
            "tags": [],
            "source_repo": "r",
            "source_ref": "x" * 40,
        },
    ]

    first = register_candidates(candidates, inventory)
    second = register_candidates(candidates, inventory)

    assert first == ["src-abc1234"]
    assert second == []
    assert len(list((tmp_path / "inventory").glob("*.yaml"))) == 1


def test_generate_daily_no_candidates_prints_sentinel(git_repo, monkeypatch):
    monkeypatch.setenv("SOURCE_SCAN_REPOS", str(git_repo))

    result = CliRunner().invoke(cli, ["generate-daily"])

    assert result.exit_code == 0
    assert result.output == "NO_CANDIDATES\n"


def test_generate_daily_dry_run_registers_nothing(git_repo, tmp_path, monkeypatch):
    _commit(git_repo, "a.txt", "Ship the thing")
    monkeypatch.setenv("SOURCE_SCAN_REPOS", str(git_repo))

    # If anything constructed an InventoryManager, the spy catches it — dry-run
    # must not touch data/inventory at all.
    inventory_spy = MagicMock()
    monkeypatch.setattr("blog_engine.core.inventory.InventoryManager", inventory_spy)

    result = CliRunner().invoke(cli, ["generate-daily", "--dry-run"])

    assert result.exit_code == 0
    assert "candidate: src-" in result.output
    assert "Ship the thing" in result.output
    assert "NO_CANDIDATES" not in result.output
    inventory_spy.assert_not_called()
    assert not (tmp_path / "inventory").exists()


def test_generate_daily_registers_then_generates(git_repo, tmp_path, monkeypatch):
    _commit(git_repo, "a.txt", "Ship daily loop")
    monkeypatch.setenv("SOURCE_SCAN_REPOS", str(git_repo))

    inventory = InventoryManager(tmp_path / "inventory")
    monkeypatch.setattr(
        "blog_engine.core.inventory.InventoryManager", lambda *a, **k: inventory
    )

    mock_db = MagicMock()
    mock_db.exec.return_value.fetchone.return_value = None
    monkeypatch.setattr(
        "blog_engine.infra.db_manager.DBManager", lambda *a, **k: mock_db
    )

    drafts_dir = tmp_path / "drafts"
    monkeypatch.setattr(
        "blog_engine.core.draft_manager.DraftManager",
        lambda *a, **k: DraftManager(mock_db, drafts_dir=drafts_dir),
    )

    with patch("blog_engine.core.generator.route") as mock_route:
        mock_route.return_value = {
            "result": "Real draft body.",
            "model_used": "test",
            "provider": "test",
        }
        result = CliRunner().invoke(cli, ["generate-daily"])

    assert result.exit_code == 0
    assert "generated: src-" in result.output
    assert "Ship daily loop" in result.output

    posts = inventory.load()
    assert len(posts) == 1
    post_id = posts[0]["post_id"]
    assert post_id.startswith("src-")
    assert (drafts_dir / f"{post_id}.json").exists()

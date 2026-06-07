"""
tests/test_env.py

Tests for .env validation and credential loading.
"""

import pytest
import os
from pathlib import Path
from dotenv import load_dotenv


def test_env_example_exists():
    """Test that .env.example exists."""
    env_example = Path(__file__).parent.parent / ".env.example"
    assert env_example.exists()


def test_env_example_has_required_keys():
    """Test that .env.example contains all required keys."""
    env_example = Path(__file__).parent.parent / ".env.example"
    
    load_dotenv(env_example)
    
    required_keys = [
        "WP_URL",
        "WP_USER",
        "WP_APP_PASSWORD",
        "DEVTO_API_KEY",
        "GROQ_API_KEY",
        "GEMINI_API_KEY",
        "OPENROUTER_API_KEY",
        "OLLAMA_MODEL",
        "LOG_LEVEL"
    ]
    
    for key in required_keys:
        # Check that the key exists in the file (even if value is placeholder)
        with open(env_example, "r") as f:
            content = f.read()
        assert key in content, f"Missing key in .env.example: {key}"


def test_env_example_format():
    """Test that .env.example has correct KEY=value format."""
    env_example = Path(__file__).parent.parent / ".env.example"
    
    with open(env_example, "r") as f:
        lines = f.readlines()
    
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#"):
            # Should be KEY=value format
            assert "=" in line, f"Invalid line format: {line}"
            key, value = line.split("=", 1)
            assert key, f"Empty key in line: {line}"


def test_log_level_valid():
    """Test that LOG_LEVEL has valid value."""
    env_example = Path(__file__).parent.parent / ".env.example"
    
    load_dotenv(env_example)
    log_level = os.getenv("LOG_LEVEL", "INFO")
    
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    assert log_level in valid_levels, f"Invalid LOG_LEVEL: {log_level}"


def test_env_not_committed():
    """Test that .env is in .gitignore."""
    gitignore = Path(__file__).parent.parent / ".gitignore"
    
    if gitignore.exists():
        with open(gitignore, "r") as f:
            content = f.read()
        assert ".env" in content, ".env should be in .gitignore"

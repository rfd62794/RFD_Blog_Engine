"""
tests/test_logger.py

Tests for structured logging setup.
"""

import pytest
import json
from pathlib import Path
import structlog


def test_logger_setup(temp_dir):
    """Test that logging setup creates log file."""
    from blog_engine.infra.logger import setup_logging
    from unittest.mock import patch
    import builtins
    
    log_file = temp_dir / "test.jsonl"
    original_open = builtins.open
    
    def mock_open(filename, mode, *args, **kwargs):
        if "jsonl" in str(filename):
            return original_open(log_file, mode)
        return original_open(filename, mode, *args, **kwargs)
    
    with patch('builtins.open', side_effect=mock_open):
        setup_logging("INFO")
        
        # Log something
        logger = structlog.get_logger("test")
        logger.info("test message", post_id="test-001")
        
        # Check log file exists and has content
        assert log_file.exists()
        
        with original_open(log_file, "r") as f:
            lines = f.readlines()
        
        assert len(lines) > 0
        
        # Parse JSON log line
        log_entry = json.loads(lines[0])
        assert log_entry["event"] == "test message"
        assert log_entry["post_id"] == "test-001"
        assert "timestamp" in log_entry
        assert "level" in log_entry


def test_logger_levels(temp_dir):
    """Test that different log levels work."""
    from blog_engine.infra.logger import setup_logging
    from unittest.mock import patch
    import builtins
    
    log_file = temp_dir / "test_levels.jsonl"
    original_open = builtins.open
    
    def mock_open(filename, mode, *args, **kwargs):
        if "jsonl" in str(filename):
            return original_open(log_file, mode)
        return original_open(filename, mode, *args, **kwargs)
    
    with patch('builtins.open', side_effect=mock_open):
        setup_logging("DEBUG")
        
        logger = structlog.get_logger("test")
        logger.debug("debug message")
        logger.info("info message")
        logger.warning("warning message")
        logger.error("error message")
        
        with original_open(log_file, "r") as f:
            lines = f.readlines()
        
        assert len(lines) == 4
        
        # Check levels
        levels = [json.loads(line)["level"] for line in lines]
        assert "debug" in levels
        assert "info" in levels
        assert "warning" in levels
        assert "error" in levels


def test_get_logger():
    """Test that get_logger returns a structlog logger."""
    from blog_engine.infra.logger import get_logger
    
    logger = get_logger("test_module")
    # structlog returns a BoundLoggerLazyProxy, not a direct BoundLogger
    # Just check it's callable and has the right interface
    assert hasattr(logger, 'info')
    assert hasattr(logger, 'error')
    assert hasattr(logger, 'warning')


def test_logger_json_output(temp_dir):
    """Test that log output is valid JSON."""
    from blog_engine.infra.logger import setup_logging
    from unittest.mock import patch
    import builtins
    
    log_file = temp_dir / "test_json.jsonl"
    original_open = builtins.open
    
    def mock_open(filename, mode, *args, **kwargs):
        if "jsonl" in str(filename):
            return original_open(log_file, mode)
        return original_open(filename, mode, *args, **kwargs)
    
    with patch('builtins.open', side_effect=mock_open):
        setup_logging("INFO")
        
        logger = structlog.get_logger("test")
        logger.info("structured test", key1="value1", key2=42)
        
        with original_open(log_file, "r") as f:
            line = f.readline()
        
        log_entry = json.loads(line)
        assert log_entry["key1"] == "value1"
        assert log_entry["key2"] == 42

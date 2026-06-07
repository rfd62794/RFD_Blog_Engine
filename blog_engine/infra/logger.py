"""
blog_engine/infra/logger.py

Structured logging setup for rfd-blog-engine.
Uses structlog with JSON output to logs/blog_engine.jsonl.
"""

import logging
import sys
from pathlib import Path
import structlog
from datetime import datetime


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure structlog for JSON output to file and console.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Ensure logs directory exists
    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "blog_engine.jsonl"
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=open(log_file, "a")),
        cache_logger_on_first_use=True,
    )
    
    # Also configure standard logging for third-party libs
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO)
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        structlog.BoundLogger
    """
    return structlog.get_logger(name)


# Initialize logging on import
# This can be called explicitly with setup_logging() if needed
_logger_initialized = False


def ensure_logging_initialized() -> None:
    """Ensure logging is initialized (idempotent)."""
    global _logger_initialized
    if not _logger_initialized:
        log_level = Path(__file__).parent.parent.parent / ".env"
        # Try to read LOG_LEVEL from .env if it exists
        try:
            from dotenv import load_dotenv
            env_file = Path(__file__).parent.parent.parent / ".env"
            if env_file.exists():
                load_dotenv(env_file)
                import os
                log_level = os.getenv("LOG_LEVEL", "INFO")
            else:
                log_level = "INFO"
        except Exception:
            log_level = "INFO"
        
        setup_logging(log_level)
        _logger_initialized = True

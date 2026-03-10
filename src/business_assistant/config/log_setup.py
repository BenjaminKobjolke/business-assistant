"""Centralized logging configuration with per-component rotating log files."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .constants import (
    DEFAULT_LOG_BACKUP_COUNT,
    DEFAULT_LOG_DIR,
    DEFAULT_LOG_LEVEL,
    DEFAULT_LOG_MAX_BYTES,
    ENV_LOG_BACKUP_COUNT,
    ENV_LOG_DIR,
    ENV_LOG_LEVEL,
    ENV_LOG_MAX_BYTES,
    LOG_FORMAT,
)


@dataclass(frozen=True)
class LoggingSettings:
    """Immutable logging configuration."""

    level: str
    log_dir: str
    max_bytes: int
    backup_count: int


def _load_logging_settings() -> LoggingSettings:
    """Read logging settings from environment variables with defaults."""
    return LoggingSettings(
        level=os.environ.get(ENV_LOG_LEVEL, DEFAULT_LOG_LEVEL).upper(),
        log_dir=os.environ.get(ENV_LOG_DIR, DEFAULT_LOG_DIR),
        max_bytes=int(os.environ.get(ENV_LOG_MAX_BYTES, DEFAULT_LOG_MAX_BYTES)),
        backup_count=int(os.environ.get(ENV_LOG_BACKUP_COUNT, DEFAULT_LOG_BACKUP_COUNT)),
    )


def _make_rotating_handler(
    log_path: Path,
    max_bytes: int,
    backup_count: int,
) -> RotatingFileHandler:
    """Create a RotatingFileHandler, ensuring the parent directory exists."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        str(log_path),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    return handler


def setup_logging() -> None:
    """Configure root logger with console output and app-namespace file handler.

    Safe to call multiple times (e.g. on restart) — existing handlers are
    cleared before new ones are added.
    """
    settings = _load_logging_settings()
    level = getattr(logging, settings.level, logging.INFO)

    root = logging.getLogger()
    # Clear existing handlers (restart-safe)
    root.handlers.clear()
    root.setLevel(level)

    # Console handler on root
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(LOG_FORMAT))
    root.addHandler(console)

    # File handler for the main bot namespace
    app_log = Path(settings.log_dir) / "app" / "app.log"
    app_handler = _make_rotating_handler(app_log, settings.max_bytes, settings.backup_count)

    app_logger = logging.getLogger("business_assistant")
    app_logger.addHandler(app_handler)


def add_plugin_logging(plugin_name: str, logger_namespace: str) -> None:
    """Add a rotating file handler for a plugin namespace.

    Creates ``logs/<plugin_name>/<plugin_name>.log`` and attaches it to
    ``logging.getLogger(logger_namespace)``.  Child loggers inherit the
    handler automatically.  Console output continues via root logger
    inheritance — no duplication.

    Idempotent: skips if a ``RotatingFileHandler`` is already present on
    the target logger (avoids duplicate handlers on restart).
    """
    settings = _load_logging_settings()

    plugin_logger = logging.getLogger(logger_namespace)

    # Idempotent check — skip if we already attached a file handler
    for h in plugin_logger.handlers:
        if isinstance(h, RotatingFileHandler):
            return

    log_path = Path(settings.log_dir) / plugin_name / f"{plugin_name}.log"
    handler = _make_rotating_handler(log_path, settings.max_bytes, settings.backup_count)
    plugin_logger.addHandler(handler)

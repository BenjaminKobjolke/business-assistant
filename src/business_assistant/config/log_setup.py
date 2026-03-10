"""Centralized logging configuration with per-component daily log files."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from .constants import (
    DEFAULT_LOG_BACKUP_COUNT,
    DEFAULT_LOG_DIR,
    DEFAULT_LOG_LEVEL,
    ENV_LOG_BACKUP_COUNT,
    ENV_LOG_DIR,
    ENV_LOG_LEVEL,
    LOG_FORMAT,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _resolve_log_dir(raw_dir: str) -> Path:
    """Resolve *raw_dir* against the project root when it is relative."""
    p = Path(raw_dir)
    if p.is_absolute():
        return p
    return _PROJECT_ROOT / p


def _close_file_handlers(target_logger: logging.Logger) -> None:
    """Close and remove all TimedRotatingFileHandlers from *target_logger*."""
    for h in target_logger.handlers[:]:
        if isinstance(h, TimedRotatingFileHandler):
            h.close()
            target_logger.removeHandler(h)


@dataclass(frozen=True)
class LoggingSettings:
    """Immutable logging configuration."""

    level: str
    log_dir: str
    backup_count: int


def _load_logging_settings() -> LoggingSettings:
    """Read logging settings from environment variables with defaults."""
    return LoggingSettings(
        level=os.environ.get(ENV_LOG_LEVEL, DEFAULT_LOG_LEVEL).upper(),
        log_dir=os.environ.get(ENV_LOG_DIR, DEFAULT_LOG_DIR),
        backup_count=int(os.environ.get(ENV_LOG_BACKUP_COUNT, DEFAULT_LOG_BACKUP_COUNT)),
    )


def _make_daily_handler(
    log_path: Path,
    backup_count: int,
) -> TimedRotatingFileHandler:
    """Create a TimedRotatingFileHandler that rotates at midnight."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = TimedRotatingFileHandler(
        str(log_path),
        when="midnight",
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
    log_dir = _resolve_log_dir(settings.log_dir)
    app_log = log_dir / "app" / "app.log"

    app_logger = logging.getLogger("business_assistant")
    _close_file_handlers(app_logger)
    app_handler = _make_daily_handler(app_log, settings.backup_count)
    app_logger.addHandler(app_handler)

    app_logger.info("File logging initialized: %s", app_log)


def add_plugin_logging(plugin_name: str, logger_namespace: str) -> None:
    """Add a daily-rotating file handler for a plugin namespace.

    Creates ``logs/<plugin_name>/<plugin_name>.log`` and attaches it to
    ``logging.getLogger(logger_namespace)``.  Child loggers inherit the
    handler automatically.  Console output continues via root logger
    inheritance — no duplication.

    Restart-safe: closes any existing ``TimedRotatingFileHandler`` on the
    target logger before attaching a fresh one.
    """
    settings = _load_logging_settings()

    plugin_logger = logging.getLogger(logger_namespace)
    _close_file_handlers(plugin_logger)

    log_dir = _resolve_log_dir(settings.log_dir)
    log_path = log_dir / plugin_name / f"{plugin_name}.log"
    handler = _make_daily_handler(log_path, settings.backup_count)
    plugin_logger.addHandler(handler)

    plugin_logger.info("Plugin file logging initialized: %s", log_path)

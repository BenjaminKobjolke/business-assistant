"""Tests for centralized logging setup."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from business_assistant.config.log_setup import (
    LoggingSettings,
    _load_logging_settings,
    add_plugin_logging,
    setup_logging,
)


class TestLoggingSettings:
    def test_frozen(self) -> None:
        settings = LoggingSettings(
            level="INFO", log_dir="logs", max_bytes=1024, backup_count=2
        )
        try:
            settings.level = "DEBUG"  # type: ignore[misc]
            raised = False
        except AttributeError:
            raised = True
        assert raised

    def test_defaults(self, monkeypatch) -> None:
        for key in ["LOG_LEVEL", "LOG_DIR", "LOG_MAX_BYTES", "LOG_BACKUP_COUNT"]:
            monkeypatch.delenv(key, raising=False)
        settings = _load_logging_settings()
        assert settings.level == "INFO"
        assert settings.log_dir == "logs"
        assert settings.max_bytes == 5_242_880
        assert settings.backup_count == 3

    def test_env_overrides(self, monkeypatch) -> None:
        monkeypatch.setenv("LOG_LEVEL", "debug")
        monkeypatch.setenv("LOG_DIR", "/tmp/custom_logs")
        monkeypatch.setenv("LOG_MAX_BYTES", "1024")
        monkeypatch.setenv("LOG_BACKUP_COUNT", "5")
        settings = _load_logging_settings()
        assert settings.level == "DEBUG"
        assert settings.log_dir == "/tmp/custom_logs"
        assert settings.max_bytes == 1024
        assert settings.backup_count == 5


class TestSetupLogging:
    def test_creates_console_handler(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
        setup_logging()
        root = logging.getLogger()
        console_handlers = [
            h for h in root.handlers if isinstance(h, logging.StreamHandler)
            and not isinstance(h, RotatingFileHandler)
        ]
        assert len(console_handlers) >= 1

    def test_creates_app_log_dir(self, tmp_path, monkeypatch) -> None:
        log_dir = tmp_path / "logs"
        monkeypatch.setenv("LOG_DIR", str(log_dir))
        setup_logging()
        assert (log_dir / "app").is_dir()

    def test_creates_file_handler_on_app_namespace(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
        setup_logging()
        app_logger = logging.getLogger("business_assistant")
        file_handlers = [h for h in app_logger.handlers if isinstance(h, RotatingFileHandler)]
        assert len(file_handlers) >= 1

    def test_clears_handlers_on_repeated_calls(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
        setup_logging()
        setup_logging()
        root = logging.getLogger()
        console_handlers = [
            h for h in root.handlers if isinstance(h, logging.StreamHandler)
            and not isinstance(h, RotatingFileHandler)
        ]
        # Should have exactly 1 console handler, not 2
        assert len(console_handlers) == 1

    def teardown_method(self) -> None:
        # Clean up handlers added during tests
        root = logging.getLogger()
        root.handlers.clear()
        app_logger = logging.getLogger("business_assistant")
        app_logger.handlers.clear()


class TestAddPluginLogging:
    def test_creates_plugin_log_dir(self, tmp_path, monkeypatch) -> None:
        log_dir = tmp_path / "logs"
        monkeypatch.setenv("LOG_DIR", str(log_dir))
        ns = "test_plugin_ns_dir"
        add_plugin_logging("testplugin", ns)
        assert (log_dir / "testplugin").is_dir()

    def test_adds_file_handler_to_namespace(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
        ns = "test_plugin_ns_handler"
        add_plugin_logging("testplugin2", ns)
        plugin_logger = logging.getLogger(ns)
        file_handlers = [h for h in plugin_logger.handlers if isinstance(h, RotatingFileHandler)]
        assert len(file_handlers) == 1

    def test_idempotent(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
        ns = "test_plugin_ns_idempotent"
        add_plugin_logging("testplugin3", ns)
        add_plugin_logging("testplugin3", ns)
        plugin_logger = logging.getLogger(ns)
        file_handlers = [h for h in plugin_logger.handlers if isinstance(h, RotatingFileHandler)]
        assert len(file_handlers) == 1

    def test_log_file_created(self, tmp_path, monkeypatch) -> None:
        log_dir = tmp_path / "logs"
        monkeypatch.setenv("LOG_DIR", str(log_dir))
        ns = "test_plugin_ns_file"
        add_plugin_logging("myplugin", ns)
        plugin_logger = logging.getLogger(ns)
        plugin_logger.info("test message")
        assert (log_dir / "myplugin" / "myplugin.log").exists()

    def teardown_method(self) -> None:
        # Clean up test loggers
        for ns in [
            "test_plugin_ns_dir",
            "test_plugin_ns_handler",
            "test_plugin_ns_idempotent",
            "test_plugin_ns_file",
        ]:
            logging.getLogger(ns).handlers.clear()

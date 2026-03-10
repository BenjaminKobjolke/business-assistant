"""Tests for centralized logging setup."""

from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from unittest.mock import MagicMock

from business_assistant.config.log_setup import (
    LoggingSettings,
    _close_file_handlers,
    _load_logging_settings,
    _resolve_log_dir,
    add_plugin_logging,
    setup_logging,
)


class TestLoggingSettings:
    def test_frozen(self) -> None:
        settings = LoggingSettings(
            level="INFO", log_dir="logs", backup_count=2
        )
        try:
            settings.level = "DEBUG"  # type: ignore[misc]
            raised = False
        except AttributeError:
            raised = True
        assert raised

    def test_defaults(self, monkeypatch) -> None:
        for key in ["LOG_LEVEL", "LOG_DIR", "LOG_BACKUP_COUNT"]:
            monkeypatch.delenv(key, raising=False)
        settings = _load_logging_settings()
        assert settings.level == "INFO"
        assert settings.log_dir == "logs"
        assert settings.backup_count == 3

    def test_env_overrides(self, monkeypatch) -> None:
        monkeypatch.setenv("LOG_LEVEL", "debug")
        monkeypatch.setenv("LOG_DIR", "/tmp/custom_logs")
        monkeypatch.setenv("LOG_BACKUP_COUNT", "5")
        settings = _load_logging_settings()
        assert settings.level == "DEBUG"
        assert settings.log_dir == "/tmp/custom_logs"
        assert settings.backup_count == 5


class TestResolveLogDir:
    def test_relative_anchored_to_project_root(self) -> None:
        result = _resolve_log_dir("logs")
        assert result.name == "logs"
        assert result.is_absolute()

    def test_absolute_unchanged(self, tmp_path) -> None:
        abs_dir = str(tmp_path / "custom_logs")
        result = _resolve_log_dir(abs_dir)
        assert result == Path(abs_dir)


class TestCloseFileHandlers:
    def test_closes_and_removes_timed_handlers(self) -> None:
        logger = logging.getLogger("test_close_timed")
        mock_handler = MagicMock(spec=TimedRotatingFileHandler)
        logger.addHandler(mock_handler)

        _close_file_handlers(logger)

        mock_handler.close.assert_called_once()
        assert mock_handler not in logger.handlers

    def test_preserves_stream_handlers(self) -> None:
        logger = logging.getLogger("test_close_preserve")
        stream_handler = logging.StreamHandler()
        logger.addHandler(stream_handler)

        _close_file_handlers(logger)

        assert stream_handler in logger.handlers

    def teardown_method(self) -> None:
        for ns in ["test_close_timed", "test_close_preserve"]:
            logging.getLogger(ns).handlers.clear()


class TestSetupLogging:
    def test_creates_console_handler(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
        setup_logging()
        root = logging.getLogger()
        console_handlers = [
            h for h in root.handlers if isinstance(h, logging.StreamHandler)
            and not isinstance(h, TimedRotatingFileHandler)
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
        file_handlers = [
            h for h in app_logger.handlers if isinstance(h, TimedRotatingFileHandler)
        ]
        assert len(file_handlers) >= 1

    def test_clears_handlers_on_repeated_calls(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
        setup_logging()
        setup_logging()
        root = logging.getLogger()
        console_handlers = [
            h for h in root.handlers if isinstance(h, logging.StreamHandler)
            and not isinstance(h, TimedRotatingFileHandler)
        ]
        # Should have exactly 1 console handler, not 2
        assert len(console_handlers) == 1

    def test_repeated_calls_no_file_handler_accumulation(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
        setup_logging()
        setup_logging()
        app_logger = logging.getLogger("business_assistant")
        file_handlers = [
            h for h in app_logger.handlers if isinstance(h, TimedRotatingFileHandler)
        ]
        assert len(file_handlers) == 1

    def test_verification_message_written(self, tmp_path, monkeypatch) -> None:
        log_dir = tmp_path / "logs"
        monkeypatch.setenv("LOG_DIR", str(log_dir))
        setup_logging()
        app_log = log_dir / "app" / "app.log"
        assert app_log.exists()
        content = app_log.read_text(encoding="utf-8")
        assert "File logging initialized" in content

    def teardown_method(self) -> None:
        # Clean up handlers added during tests
        root = logging.getLogger()
        root.handlers.clear()
        app_logger = logging.getLogger("business_assistant")
        for h in app_logger.handlers[:]:
            if isinstance(h, TimedRotatingFileHandler):
                h.close()
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
        file_handlers = [
            h for h in plugin_logger.handlers if isinstance(h, TimedRotatingFileHandler)
        ]
        assert len(file_handlers) == 1

    def test_idempotent(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
        ns = "test_plugin_ns_idempotent"
        add_plugin_logging("testplugin3", ns)
        first_logger = logging.getLogger(ns)
        first_handlers = [
            h for h in first_logger.handlers if isinstance(h, TimedRotatingFileHandler)
        ]
        assert len(first_handlers) == 1
        old_handler = first_handlers[0]

        # Second call should close old handler and add a fresh one
        add_plugin_logging("testplugin3", ns)
        new_handlers = [
            h for h in first_logger.handlers if isinstance(h, TimedRotatingFileHandler)
        ]
        assert len(new_handlers) == 1
        assert new_handlers[0] is not old_handler

    def test_log_file_created(self, tmp_path, monkeypatch) -> None:
        log_dir = tmp_path / "logs"
        monkeypatch.setenv("LOG_DIR", str(log_dir))
        ns = "test_plugin_ns_file"
        add_plugin_logging("myplugin", ns)
        plugin_logger = logging.getLogger(ns)
        plugin_logger.info("test message")
        assert (log_dir / "myplugin" / "myplugin.log").exists()

    def test_verification_message_written(self, tmp_path, monkeypatch) -> None:
        log_dir = tmp_path / "logs"
        monkeypatch.setenv("LOG_DIR", str(log_dir))
        ns = "test_plugin_ns_verify"
        add_plugin_logging("verifyplugin", ns)
        log_file = log_dir / "verifyplugin" / "verifyplugin.log"
        assert log_file.exists()
        content = log_file.read_text(encoding="utf-8")
        assert "Plugin file logging initialized" in content

    def test_child_logger_propagates(self, tmp_path, monkeypatch) -> None:
        log_dir = tmp_path / "logs"
        monkeypatch.setenv("LOG_DIR", str(log_dir))
        ns = "test_plugin_ns_child"
        add_plugin_logging("childplugin", ns)
        child = logging.getLogger(f"{ns}.submodule")
        child.setLevel(logging.DEBUG)
        child.info("child message")
        log_file = log_dir / "childplugin" / "childplugin.log"
        content = log_file.read_text(encoding="utf-8")
        assert "child message" in content

    def teardown_method(self) -> None:
        # Clean up test loggers
        for ns in [
            "test_plugin_ns_dir",
            "test_plugin_ns_handler",
            "test_plugin_ns_idempotent",
            "test_plugin_ns_file",
            "test_plugin_ns_verify",
            "test_plugin_ns_child",
            "test_plugin_ns_child.submodule",
        ]:
            logger = logging.getLogger(ns)
            for h in logger.handlers[:]:
                if isinstance(h, TimedRotatingFileHandler):
                    h.close()
            logger.handlers.clear()

"""Tests for FileHandlerRegistry."""

from __future__ import annotations

from business_assistant.files.downloader import DownloadedFile
from business_assistant.files.handler_registry import (
    FileHandlerRegistry,
    FileHandlerResult,
)
from business_assistant.plugins.registry import PluginRegistry


def _dummy_handler(downloaded: DownloadedFile, user_id: str) -> FileHandlerResult:
    return FileHandlerResult(summary="handled")


class TestFileHandlerResult:
    def test_create(self) -> None:
        r = FileHandlerResult(summary="done")
        assert r.summary == "done"
        assert r.processed is True

    def test_not_processed(self) -> None:
        r = FileHandlerResult(summary="skipped", processed=False)
        assert r.processed is False


class TestFileHandlerRegistry:
    def test_exact_mime_match(self) -> None:
        registry = FileHandlerRegistry()
        registry.register(["audio/ogg"], "audio-plugin", _dummy_handler)

        handlers = registry.get_handlers("audio/ogg")
        assert len(handlers) == 1
        assert handlers[0][0] == "audio-plugin"

    def test_wildcard_mime_match(self) -> None:
        registry = FileHandlerRegistry()
        registry.register(["audio/*"], "audio-plugin", _dummy_handler)

        handlers = registry.get_handlers("audio/ogg")
        assert len(handlers) == 1

        handlers = registry.get_handlers("audio/mpeg")
        assert len(handlers) == 1

    def test_no_match(self) -> None:
        registry = FileHandlerRegistry()
        registry.register(["audio/*"], "audio-plugin", _dummy_handler)

        handlers = registry.get_handlers("image/png")
        assert len(handlers) == 0

    def test_multiple_handlers(self) -> None:
        registry = FileHandlerRegistry()
        registry.register(["audio/ogg"], "plugin-a", _dummy_handler)
        registry.register(["audio/*"], "plugin-b", _dummy_handler)

        handlers = registry.get_handlers("audio/ogg")
        assert len(handlers) == 2
        names = {h[0] for h in handlers}
        assert names == {"plugin-a", "plugin-b"}

    def test_empty_registry(self) -> None:
        registry = FileHandlerRegistry()
        assert registry.get_handlers("audio/ogg") == []


class TestPluginRegistryFileHandler:
    def test_register_file_handler_creates_registry(self) -> None:
        registry = PluginRegistry()
        registry.register_file_handler(["audio/*"], "test-plugin", _dummy_handler)

        from business_assistant.config.constants import PLUGIN_DATA_FILE_HANDLERS

        assert PLUGIN_DATA_FILE_HANDLERS in registry.plugin_data
        assert isinstance(registry.plugin_data[PLUGIN_DATA_FILE_HANDLERS], FileHandlerRegistry)

    def test_register_file_handler_reuses_registry(self) -> None:
        registry = PluginRegistry()
        registry.register_file_handler(["audio/*"], "plugin-a", _dummy_handler)
        registry.register_file_handler(["image/*"], "plugin-b", _dummy_handler)

        from business_assistant.config.constants import PLUGIN_DATA_FILE_HANDLERS

        handler_registry = registry.plugin_data[PLUGIN_DATA_FILE_HANDLERS]
        assert len(handler_registry.get_handlers("audio/ogg")) == 1
        assert len(handler_registry.get_handlers("image/png")) == 1

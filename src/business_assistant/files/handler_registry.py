"""Registry for plugin-provided file type handlers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from fnmatch import fnmatch

from business_assistant.files.downloader import DownloadedFile


@dataclass(frozen=True)
class FileHandlerResult:
    """Result returned by a file handler."""

    summary: str
    processed: bool = True


FileHandlerFn = Callable[[DownloadedFile, str], FileHandlerResult]


class FileHandlerRegistry:
    """Matches MIME types to plugin-registered handler functions."""

    def __init__(self) -> None:
        self._handlers: list[tuple[str, str, FileHandlerFn]] = []

    def register(
        self, mime_patterns: list[str], plugin_name: str, handler: FileHandlerFn
    ) -> None:
        """Register a handler for one or more MIME patterns (e.g. ``audio/*``)."""
        for pattern in mime_patterns:
            self._handlers.append((pattern, plugin_name, handler))

    def get_handlers(self, mime_type: str) -> list[tuple[str, FileHandlerFn]]:
        """Return ``(plugin_name, handler)`` pairs matching *mime_type*.

        Checks exact match first, then wildcard (``audio/*``).
        """
        matches: list[tuple[str, FileHandlerFn]] = []
        for pattern, plugin_name, handler in self._handlers:
            if pattern == mime_type or fnmatch(mime_type, pattern):
                matches.append((plugin_name, handler))
        return matches

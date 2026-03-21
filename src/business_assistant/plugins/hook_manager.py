"""Plugin hook management for file handlers, processors and modifiers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from business_assistant.config.constants import (
    PLUGIN_DATA_COMMAND_HANDLERS,
    PLUGIN_DATA_FILE_HANDLERS,
    PLUGIN_DATA_MESSAGE_MODIFIERS,
    PLUGIN_DATA_RESPONSE_PROCESSORS,
)


class PluginHookManager:
    """Manages plugin hooks stored in the plugin_data dict."""

    def __init__(self, plugin_data: dict[str, Any]) -> None:
        self._plugin_data = plugin_data

    def register_file_handler(
        self,
        mime_patterns: list[str],
        plugin_name: str,
        handler: Callable,
    ) -> None:
        """Register a file type handler. Creates FileHandlerRegistry in plugin_data if needed."""
        from business_assistant.files.handler_registry import FileHandlerRegistry

        if PLUGIN_DATA_FILE_HANDLERS not in self._plugin_data:
            self._plugin_data[PLUGIN_DATA_FILE_HANDLERS] = FileHandlerRegistry()
        self._plugin_data[PLUGIN_DATA_FILE_HANDLERS].register(
            mime_patterns, plugin_name, handler
        )

    def register_response_processor(self, processor: Callable) -> None:
        """Register a response processor that transforms responses before sending.

        Processors are called in registration order with signature:
        ``(BotResponse, user_id: str, plugin_data: dict) -> BotResponse``
        """
        if PLUGIN_DATA_RESPONSE_PROCESSORS not in self._plugin_data:
            self._plugin_data[PLUGIN_DATA_RESPONSE_PROCESSORS] = []
        self._plugin_data[PLUGIN_DATA_RESPONSE_PROCESSORS].append(processor)

    def register_command_handler(self, handler: Callable) -> None:
        """Register a command handler that intercepts messages before the AI.

        Handlers are called in registration order with signature:
        ``(text: str, user_id: str, plugin_data: dict) -> BotResponse | None``

        Return a BotResponse to short-circuit (skip AI), or None to continue.
        """
        if PLUGIN_DATA_COMMAND_HANDLERS not in self._plugin_data:
            self._plugin_data[PLUGIN_DATA_COMMAND_HANDLERS] = []
        self._plugin_data[PLUGIN_DATA_COMMAND_HANDLERS].append(handler)

    def register_message_modifier(self, modifier: Callable) -> None:
        """Register a message modifier that transforms text before the AI sees it.

        Modifiers are called in registration order with signature:
        ``(text: str, user_id: str, plugin_data: dict) -> str``
        """
        if PLUGIN_DATA_MESSAGE_MODIFIERS not in self._plugin_data:
            self._plugin_data[PLUGIN_DATA_MESSAGE_MODIFIERS] = []
        self._plugin_data[PLUGIN_DATA_MESSAGE_MODIFIERS].append(modifier)

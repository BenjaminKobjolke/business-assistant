"""Plugin registry for collecting tools and system prompt extras."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from business_assistant.config.constants import (
    PLUGIN_DATA_COMMAND_HANDLERS,
    PLUGIN_DATA_FILE_HANDLERS,
    PLUGIN_DATA_MESSAGE_MODIFIERS,
    PLUGIN_DATA_RESPONSE_PROCESSORS,
)


class PluginCategoryConflictError(Exception):
    """Raised when two plugins try to register the same category."""

    def __init__(self, category: str, existing_plugin: str, new_plugin: str) -> None:
        super().__init__(
            f"Category '{category}' conflict: already provided by "
            f"'{existing_plugin}', cannot register '{new_plugin}'"
        )


@dataclass
class PluginInfo:
    """Metadata about a registered plugin."""

    name: str
    description: str
    system_prompt_extra: str = ""
    category: str = ""
    required_categories: tuple[str, ...] = ()


class PluginRegistry:
    """Collects PydanticAI tools and prompt extras from plugins."""

    def __init__(self, plugin_data: dict[str, Any] | None = None) -> None:
        self._plugins: list[PluginInfo] = []
        self._tools: list[Any] = []
        self._tool_plugin_map: dict[str, str] = {}
        self._category_map: dict[str, PluginInfo] = {}
        self.plugin_data: dict[str, Any] = plugin_data if plugin_data is not None else {}

    def register(self, info: PluginInfo, tools: list[Any]) -> None:
        """Register a plugin with its info and PydanticAI Tool objects."""
        if info.category and info.category in self._category_map:
            existing = self._category_map[info.category]
            raise PluginCategoryConflictError(
                info.category, existing.name, info.name
            )
        self._plugins.append(info)
        self._tools.extend(tools)
        for tool in tools:
            self._tool_plugin_map[tool.name] = info.name
        if info.category:
            self._category_map[info.category] = info

    def all_tools(self) -> list[Any]:
        """Return all registered PydanticAI Tool objects."""
        return list(self._tools)

    def system_prompt_extras(self) -> str:
        """Combine all plugin system prompt extras into a single string."""
        extras = [p.system_prompt_extra for p in self._plugins if p.system_prompt_extra]
        return "\n\n".join(extras)

    def tool_plugin_map(self) -> dict[str, str]:
        """Return a copy of the tool-name-to-plugin-name mapping."""
        return dict(self._tool_plugin_map)

    def plugin_for_tool(self, tool_name: str, default: str = "core") -> str:
        """Return the plugin name for a tool, or *default* if unknown."""
        return self._tool_plugin_map.get(tool_name, default)

    def plugin_for_category(self, category: str) -> PluginInfo | None:
        """Return the PluginInfo registered for *category*, or None."""
        return self._category_map.get(category)

    def validate_category_requirements(self) -> list[str]:
        """Check all plugins' required_categories and return error messages for unmet ones."""
        errors: list[str] = []
        for plugin in self._plugins:
            for cat in plugin.required_categories:
                if cat not in self._category_map:
                    errors.append(
                        f"Plugin '{plugin.name}' requires category '{cat}' "
                        f"but no plugin provides it"
                    )
        return errors

    def register_file_handler(
        self,
        mime_patterns: list[str],
        plugin_name: str,
        handler: Callable,
    ) -> None:
        """Register a file type handler. Creates FileHandlerRegistry in plugin_data if needed."""
        from business_assistant.files.handler_registry import FileHandlerRegistry

        if PLUGIN_DATA_FILE_HANDLERS not in self.plugin_data:
            self.plugin_data[PLUGIN_DATA_FILE_HANDLERS] = FileHandlerRegistry()
        self.plugin_data[PLUGIN_DATA_FILE_HANDLERS].register(
            mime_patterns, plugin_name, handler
        )

    def register_response_processor(self, processor: Callable) -> None:
        """Register a response processor that transforms responses before sending.

        Processors are called in registration order with signature:
        ``(BotResponse, user_id: str, plugin_data: dict) -> BotResponse``
        """
        if PLUGIN_DATA_RESPONSE_PROCESSORS not in self.plugin_data:
            self.plugin_data[PLUGIN_DATA_RESPONSE_PROCESSORS] = []
        self.plugin_data[PLUGIN_DATA_RESPONSE_PROCESSORS].append(processor)

    def register_command_handler(self, handler: Callable) -> None:
        """Register a command handler that intercepts messages before the AI.

        Handlers are called in registration order with signature:
        ``(text: str, user_id: str, plugin_data: dict) -> BotResponse | None``

        Return a BotResponse to short-circuit (skip AI), or None to continue.
        """
        if PLUGIN_DATA_COMMAND_HANDLERS not in self.plugin_data:
            self.plugin_data[PLUGIN_DATA_COMMAND_HANDLERS] = []
        self.plugin_data[PLUGIN_DATA_COMMAND_HANDLERS].append(handler)

    def register_message_modifier(self, modifier: Callable) -> None:
        """Register a message modifier that transforms text before the AI sees it.

        Modifiers are called in registration order with signature:
        ``(text: str, user_id: str, plugin_data: dict) -> str``
        """
        if PLUGIN_DATA_MESSAGE_MODIFIERS not in self.plugin_data:
            self.plugin_data[PLUGIN_DATA_MESSAGE_MODIFIERS] = []
        self.plugin_data[PLUGIN_DATA_MESSAGE_MODIFIERS].append(modifier)

    @property
    def plugins(self) -> list[PluginInfo]:
        """Return list of registered plugin infos."""
        return list(self._plugins)

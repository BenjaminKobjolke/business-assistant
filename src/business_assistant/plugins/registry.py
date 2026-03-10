"""Plugin registry for collecting tools and system prompt extras."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PluginInfo:
    """Metadata about a registered plugin."""

    name: str
    description: str
    system_prompt_extra: str = ""


class PluginRegistry:
    """Collects PydanticAI tools and prompt extras from plugins."""

    def __init__(self, plugin_data: dict[str, Any] | None = None) -> None:
        self._plugins: list[PluginInfo] = []
        self._tools: list[Any] = []
        self._tool_plugin_map: dict[str, str] = {}
        self.plugin_data: dict[str, Any] = plugin_data if plugin_data is not None else {}

    def register(self, info: PluginInfo, tools: list[Any]) -> None:
        """Register a plugin with its info and PydanticAI Tool objects."""
        self._plugins.append(info)
        self._tools.extend(tools)
        for tool in tools:
            self._tool_plugin_map[tool.name] = info.name

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

    @property
    def plugins(self) -> list[PluginInfo]:
        """Return list of registered plugin infos."""
        return list(self._plugins)

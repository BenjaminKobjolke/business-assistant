"""Test that total tool count stays within OpenAI's limit.

This test loads all plugins listed in .env PLUGINS and counts the total
tools (core + plugin). Plugins that skip registration due to missing
config (e.g., IMAP_SERVER) are excluded from the count.
"""

from __future__ import annotations

from pathlib import Path

from business_assistant.config.constants import OPENAI_MAX_TOOLS
from business_assistant.plugins.loader import load_plugins
from business_assistant.plugins.registry import PluginRegistry

# Core tools registered in create_agent() (memory + feedback + synonyms)
CORE_TOOL_COUNT = 10

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _get_plugin_names_from_env_file() -> list[str]:
    """Read plugin names from the .env file's PLUGINS variable."""
    env_file = _PROJECT_ROOT / ".env"
    if not env_file.is_file():
        return []
    for line in env_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("PLUGINS="):
            raw = stripped.split("=", 1)[1]
            return [n.strip() for n in raw.split(",") if n.strip()]
    return []


class TestToolCount:
    def test_total_tools_within_openai_limit(self) -> None:
        """Ensure the total number of registered tools stays under 128.

        Loads all plugins from .env PLUGINS and counts tools.
        Plugins that skip registration (missing config) are not counted.
        """
        plugin_names = _get_plugin_names_from_env_file()
        if not plugin_names:
            return

        registry = PluginRegistry()
        load_plugins(registry, plugin_names)

        plugin_tools = len(registry.all_tools())
        total = CORE_TOOL_COUNT + plugin_tools

        assert total < OPENAI_MAX_TOOLS, (
            f"Total tool count ({total}) reaches or exceeds OpenAI limit "
            f"({OPENAI_MAX_TOOLS}). Core: {CORE_TOOL_COUNT}, "
            f"Plugins: {plugin_tools}. "
            f"Consolidate tools to reduce the count."
        )

    def test_tool_names_are_unique(self) -> None:
        """Ensure no duplicate tool names across all plugins."""
        plugin_names = _get_plugin_names_from_env_file()
        if not plugin_names:
            return

        registry = PluginRegistry()
        load_plugins(registry, plugin_names)

        names = [t.name for t in registry.all_tools()]
        duplicates = [n for n in names if names.count(n) > 1]
        assert not duplicates, (
            f"Duplicate tool names found: {set(duplicates)}"
        )

"""Tests for the plugin registry."""

from __future__ import annotations

from unittest.mock import MagicMock

from business_assistant.plugins.registry import PluginInfo, PluginRegistry


class TestPluginRegistry:
    def test_register_and_collect_tools(self) -> None:
        registry = PluginRegistry()
        info = PluginInfo(name="test", description="Test plugin")
        tool_a = _mock_tool("tool_a")
        tool_b = _mock_tool("tool_b")
        registry.register(info, [tool_a, tool_b])

        assert registry.all_tools() == [tool_a, tool_b]
        assert len(registry.plugins) == 1
        assert registry.plugins[0].name == "test"

    def test_multiple_plugins(self) -> None:
        registry = PluginRegistry()
        registry.register(
            PluginInfo(name="p1", description="Plugin 1"),
            [_mock_tool("t1")],
        )
        registry.register(
            PluginInfo(name="p2", description="Plugin 2"),
            [_mock_tool("t2"), _mock_tool("t3")],
        )

        assert len(registry.all_tools()) == 3
        assert len(registry.plugins) == 2

    def test_system_prompt_extras(self) -> None:
        registry = PluginRegistry()
        registry.register(
            PluginInfo(name="email", description="Email", system_prompt_extra="Can read emails"),
            [],
        )
        registry.register(
            PluginInfo(
                name="calendar", description="Calendar", system_prompt_extra="Can manage calendar"
            ),
            [],
        )

        extras = registry.system_prompt_extras()
        assert "Can read emails" in extras
        assert "Can manage calendar" in extras

    def test_empty_extras_skipped(self) -> None:
        registry = PluginRegistry()
        registry.register(
            PluginInfo(name="p1", description="P1", system_prompt_extra=""),
            [],
        )
        registry.register(
            PluginInfo(name="p2", description="P2", system_prompt_extra="Extra"),
            [],
        )

        assert registry.system_prompt_extras() == "Extra"

    def test_empty_registry(self) -> None:
        registry = PluginRegistry()
        assert registry.all_tools() == []
        assert registry.system_prompt_extras() == ""
        assert registry.plugins == []


def _mock_tool(name: str) -> MagicMock:
    """Create a mock PydanticAI Tool with a .name attribute."""
    tool = MagicMock()
    tool.name = name
    return tool


class TestToolPluginMap:
    def test_maps_tools_to_plugin(self) -> None:
        registry = PluginRegistry()
        tools = [_mock_tool("search_emails"), _mock_tool("show_email")]
        registry.register(PluginInfo(name="imap", description="Email"), tools)

        mapping = registry.tool_plugin_map()
        assert mapping == {"search_emails": "imap", "show_email": "imap"}

    def test_multiple_plugins_mapped(self) -> None:
        registry = PluginRegistry()
        registry.register(
            PluginInfo(name="imap", description="Email"),
            [_mock_tool("search_emails")],
        )
        registry.register(
            PluginInfo(name="calendar", description="Calendar"),
            [_mock_tool("list_events")],
        )

        mapping = registry.tool_plugin_map()
        assert mapping == {"search_emails": "imap", "list_events": "calendar"}

    def test_tool_plugin_map_returns_copy(self) -> None:
        registry = PluginRegistry()
        registry.register(
            PluginInfo(name="imap", description="Email"),
            [_mock_tool("search")],
        )
        m1 = registry.tool_plugin_map()
        m1["extra"] = "modified"
        assert "extra" not in registry.tool_plugin_map()

    def test_plugin_for_tool_known(self) -> None:
        registry = PluginRegistry()
        registry.register(
            PluginInfo(name="imap", description="Email"),
            [_mock_tool("search_emails")],
        )
        assert registry.plugin_for_tool("search_emails") == "imap"

    def test_plugin_for_tool_unknown(self) -> None:
        registry = PluginRegistry()
        assert registry.plugin_for_tool("unknown_tool") == "core"

    def test_plugin_for_tool_custom_default(self) -> None:
        registry = PluginRegistry()
        assert registry.plugin_for_tool("unknown", default="other") == "other"

    def test_empty_registry_map(self) -> None:
        registry = PluginRegistry()
        assert registry.tool_plugin_map() == {}

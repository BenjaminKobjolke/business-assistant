"""Tests for the plugin registry."""

from __future__ import annotations

from business_assistant.plugins.registry import PluginInfo, PluginRegistry


class TestPluginRegistry:
    def test_register_and_collect_tools(self) -> None:
        registry = PluginRegistry()
        info = PluginInfo(name="test", description="Test plugin")
        tools = ["tool_a", "tool_b"]
        registry.register(info, tools)

        assert registry.all_tools() == ["tool_a", "tool_b"]
        assert len(registry.plugins) == 1
        assert registry.plugins[0].name == "test"

    def test_multiple_plugins(self) -> None:
        registry = PluginRegistry()
        registry.register(
            PluginInfo(name="p1", description="Plugin 1"),
            ["t1"],
        )
        registry.register(
            PluginInfo(name="p2", description="Plugin 2"),
            ["t2", "t3"],
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

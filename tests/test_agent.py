"""Tests for agent creation and tool wiring."""

from pydantic_ai import RunContext, Tool
from pydantic_ai.models.test import TestModel

from business_assistant.agent.agent import create_agent
from business_assistant.agent.deps import Deps
from business_assistant.memory.store import MemoryStore
from business_assistant.plugins.registry import PluginInfo, PluginRegistry


class TestAgentCreation:
    def test_create_agent_with_memory_tools(self, tmp_memory_file: str) -> None:
        memory = MemoryStore(tmp_memory_file)
        registry = PluginRegistry()

        agent = create_agent(registry, memory, TestModel())

        tool_names = {t.name for t in agent._function_toolset.tools.values()}
        assert "memory_get" in tool_names
        assert "memory_set" in tool_names
        assert "memory_delete" in tool_names
        assert "memory_list" in tool_names

    def test_create_agent_with_plugin_tools(self, tmp_memory_file: str) -> None:
        def dummy_tool(ctx: RunContext[Deps]) -> str:
            return "dummy"

        memory = MemoryStore(tmp_memory_file)
        registry = PluginRegistry()
        registry.register(
            PluginInfo(name="test", description="Test"),
            [Tool(dummy_tool, name="test_tool", description="A test tool")],
        )

        agent = create_agent(registry, memory, TestModel())

        tool_names = {t.name for t in agent._function_toolset.tools.values()}
        assert "test_tool" in tool_names
        assert "memory_get" in tool_names

"""Tests for agent creation and tool wiring."""

from unittest.mock import MagicMock

from pydantic_ai import RunContext, Tool
from pydantic_ai.models.test import TestModel

from business_assistant.agent.agent import _write_feedback, create_agent
from business_assistant.agent.deps import Deps
from business_assistant.memory.store import MemoryStore
from business_assistant.plugins.registry import PluginInfo, PluginRegistry
from tests.conftest import make_test_settings


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

    def test_create_agent_has_write_feedback_tool(self, tmp_memory_file: str) -> None:
        memory = MemoryStore(tmp_memory_file)
        registry = PluginRegistry()
        agent = create_agent(registry, memory, TestModel())
        tool_names = {t.name for t in agent._function_toolset.tools.values()}
        assert "write_feedback" in tool_names


class TestWriteFeedback:
    def test_creates_feedback_file(self, tmp_path, monkeypatch) -> None:
        feedback_dir = tmp_path / "feedback"
        monkeypatch.setenv("FEEDBACK_DIR", str(feedback_dir))

        settings = make_test_settings()
        deps = Deps(
            memory=MemoryStore(str(tmp_path / "mem.json")),
            settings=settings,
            user_id="tester@test.com",
            plugin_data={},
        )
        ctx = MagicMock(spec=RunContext)
        ctx.deps = deps

        result = _write_feedback(ctx, "search broken", "search_emails returned 0 results")
        assert "Feedback saved" in result
        assert feedback_dir.is_dir()

        files = list(feedback_dir.glob("*.md"))
        assert len(files) == 1
        content = files[0].read_text(encoding="utf-8")
        assert "search broken" in content
        assert "search_emails returned 0 results" in content
        assert "tester@test.com" in content

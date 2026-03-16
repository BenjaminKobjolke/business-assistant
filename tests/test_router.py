"""Tests for AI-based category router."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from pydantic_ai import Tool
from pydantic_ai.usage import RunUsage

from business_assistant.agent.router import (
    CategoryRouter,
    CategorySelection,
    RoutingResult,
)
from business_assistant.plugins.registry import PluginInfo, PluginRegistry


def _make_registry() -> PluginRegistry:
    """Create a registry with test plugins spanning multiple categories."""
    registry = PluginRegistry()

    def dummy(ctx) -> str:
        return "ok"

    registry.register(
        PluginInfo(name="email_plugin", description="Email operations", category="email"),
        [Tool(dummy, name="list_emails")],
    )
    registry.register(
        PluginInfo(
            name="calendar_plugin", description="Calendar management",
            category="calendar",
        ),
        [Tool(dummy, name="list_events")],
    )
    registry.register(
        PluginInfo(
            name="pm_plugin", description="Project management",
            category="project_management",
            required_categories=("email", "todo"),
        ),
        [Tool(dummy, name="pm_create")],
    )
    registry.register(
        PluginInfo(name="todo_plugin", description="Task management", category="todo"),
        [Tool(dummy, name="add_task")],
    )
    # Uncategorized plugin (always included)
    registry.register(
        PluginInfo(name="transcribe_plugin", description="Audio transcription"),
        [Tool(dummy, name="transcribe")],
    )
    return registry


class TestRoutingResult:
    def test_carries_usage(self) -> None:
        usage = RunUsage()
        result = RoutingResult(categories={"email"}, usage=usage)
        assert result.usage is usage

    def test_carries_none_usage(self) -> None:
        result = RoutingResult(categories={"email"}, usage=None)
        assert result.usage is None


class TestCategoryRouter:
    @patch("business_assistant.agent.router.Agent")
    def test_route_selects_valid_categories(self, mock_agent_cls) -> None:
        registry = _make_registry()
        mock_result = MagicMock()
        mock_result.output = CategorySelection(categories=["email", "calendar"])
        mock_result.usage.return_value = RunUsage()
        mock_agent_cls.return_value.run_sync.return_value = mock_result

        router = CategoryRouter(registry, model="openai:gpt-5-mini", model_name="gpt-5-mini")
        result = router.route("check my emails and meetings")

        assert result.categories == {"email", "calendar"}
        assert result.usage is not None

    @patch("business_assistant.agent.router.Agent")
    def test_route_filters_hallucinated_categories(self, mock_agent_cls) -> None:
        registry = _make_registry()
        mock_result = MagicMock()
        mock_result.output = CategorySelection(
            categories=["email", "nonexistent_category"],
        )
        mock_result.usage.return_value = RunUsage()
        mock_agent_cls.return_value.run_sync.return_value = mock_result

        router = CategoryRouter(registry, model="openai:gpt-5-mini", model_name="gpt-5-mini")
        result = router.route("something")

        assert "email" in result.categories
        assert "nonexistent_category" not in result.categories

    @patch("business_assistant.agent.router.Agent")
    def test_route_expands_dependencies(self, mock_agent_cls) -> None:
        registry = _make_registry()
        mock_result = MagicMock()
        mock_result.output = CategorySelection(categories=["project_management"])
        mock_result.usage.return_value = RunUsage()
        mock_agent_cls.return_value.run_sync.return_value = mock_result

        router = CategoryRouter(registry, model="openai:gpt-5-mini", model_name="gpt-5-mini")
        result = router.route("create project from email")

        assert "project_management" in result.categories
        assert "email" in result.categories
        assert "todo" in result.categories

    @patch("business_assistant.agent.router.Agent")
    def test_route_fallback_on_exception(self, mock_agent_cls) -> None:
        registry = _make_registry()
        mock_agent_cls.return_value.run_sync.side_effect = RuntimeError("API error")

        router = CategoryRouter(registry, model="openai:gpt-5-mini", model_name="gpt-5-mini")
        result = router.route("anything")

        assert result.categories == registry.all_categories()
        assert result.usage is None

    @patch("business_assistant.agent.router.Agent")
    def test_route_empty_selection(self, mock_agent_cls) -> None:
        registry = _make_registry()
        mock_result = MagicMock()
        mock_result.output = CategorySelection(categories=[])
        mock_result.usage.return_value = RunUsage()
        mock_agent_cls.return_value.run_sync.return_value = mock_result

        router = CategoryRouter(registry, model="openai:gpt-5-mini", model_name="gpt-5-mini")
        result = router.route("hello")

        assert result.categories == set()

    def test_model_name_property(self) -> None:
        registry = _make_registry()
        with patch("business_assistant.agent.router.Agent"):
            router = CategoryRouter(
                registry, model="openai:gpt-5-mini", model_name="gpt-5-mini",
            )
        assert router.model_name == "gpt-5-mini"

    def test_model_name_from_object_model(self) -> None:
        registry = _make_registry()
        mock_model = MagicMock()
        with patch("business_assistant.agent.router.Agent"):
            router = CategoryRouter(
                registry, model=mock_model, model_name="deepseek-chat",
            )
        assert router.model_name == "deepseek-chat"

    def test_prompt_contains_all_categories(self) -> None:
        registry = _make_registry()
        with patch("business_assistant.agent.router.Agent"):
            router = CategoryRouter(
                registry, model="openai:gpt-5-mini", model_name="gpt-5-mini",
            )
        prompt = router._system_prompt
        assert "email" in prompt
        assert "calendar" in prompt
        assert "project_management" in prompt
        assert "todo" in prompt

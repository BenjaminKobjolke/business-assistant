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


class TestCategoryRouterStructured:
    """Tests for structured output mode (non-Ollama providers)."""

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
    def test_route_empty_selection(self, mock_agent_cls) -> None:
        registry = _make_registry()
        mock_result = MagicMock()
        mock_result.output = CategorySelection(categories=[])
        mock_result.usage.return_value = RunUsage()
        mock_agent_cls.return_value.run_sync.return_value = mock_result

        router = CategoryRouter(registry, model="openai:gpt-5-mini", model_name="gpt-5-mini")
        result = router.route("hello")

        assert result.categories == set()

    @patch("business_assistant.agent.router.Agent")
    def test_retries_passed_to_agent(self, mock_agent_cls) -> None:
        registry = _make_registry()
        CategoryRouter(
            registry, model="openai:gpt-5-mini", model_name="gpt-5-mini", retries=5,
        )
        call_kwargs = mock_agent_cls.call_args[1]
        assert call_kwargs["retries"] == 5


class TestCategoryRouterTextMode:
    """Tests for text parsing mode (Ollama provider)."""

    @patch("business_assistant.agent.router.Agent")
    def test_route_parses_json_array(self, mock_agent_cls) -> None:
        registry = _make_registry()
        mock_result = MagicMock()
        mock_result.output = '["email", "calendar"]'
        mock_result.usage.return_value = RunUsage()
        mock_agent_cls.return_value.run_sync.return_value = mock_result

        router = CategoryRouter(
            registry, model="ollama:qwen", model_name="qwen",
            provider="ollama",
        )
        result = router.route("check my emails")

        assert result.categories == {"email", "calendar"}

    @patch("business_assistant.agent.router.Agent")
    def test_route_parses_embedded_array(self, mock_agent_cls) -> None:
        registry = _make_registry()
        mock_result = MagicMock()
        mock_result.output = 'The categories are: ["email"]'
        mock_result.usage.return_value = RunUsage()
        mock_agent_cls.return_value.run_sync.return_value = mock_result

        router = CategoryRouter(
            registry, model="ollama:qwen", model_name="qwen",
            provider="ollama",
        )
        result = router.route("check emails")

        assert result.categories == {"email"}

    @patch("business_assistant.agent.router.Agent")
    def test_route_parses_empty_array(self, mock_agent_cls) -> None:
        registry = _make_registry()
        mock_result = MagicMock()
        mock_result.output = "[]"
        mock_result.usage.return_value = RunUsage()
        mock_agent_cls.return_value.run_sync.return_value = mock_result

        router = CategoryRouter(
            registry, model="ollama:qwen", model_name="qwen",
            provider="ollama",
        )
        result = router.route("hello")

        assert result.categories == set()

    @patch("business_assistant.agent.router.Agent")
    def test_no_retries_in_text_mode(self, mock_agent_cls) -> None:
        registry = _make_registry()
        CategoryRouter(
            registry, model="ollama:qwen", model_name="qwen",
            retries=5, provider="ollama",
        )
        call_kwargs = mock_agent_cls.call_args[1]
        assert "retries" not in call_kwargs


class TestCategoryRouterCommon:
    """Tests shared across both modes."""

    @patch("business_assistant.agent.router.Agent")
    def test_route_fallback_on_exception(self, mock_agent_cls) -> None:
        registry = _make_registry()
        mock_agent_cls.return_value.run_sync.side_effect = RuntimeError("API error")

        router = CategoryRouter(registry, model="openai:gpt-5-mini", model_name="gpt-5-mini")
        result = router.route("anything")

        assert result.categories == set()
        assert result.failed is True
        assert result.usage is not None
        assert result.usage.requests == 1
        assert result.usage.input_tokens == 0

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


class TestParseCategories:
    def test_plain_json_array(self) -> None:
        assert CategoryRouter._parse_categories('["email"]') == ["email"]

    def test_markdown_fenced(self) -> None:
        text = '```json\n["email", "calendar"]\n```'
        assert CategoryRouter._parse_categories(text) == ["email", "calendar"]

    def test_embedded_in_text(self) -> None:
        text = 'Based on the message: ["todo", "email"]'
        assert CategoryRouter._parse_categories(text) == ["todo", "email"]

    def test_invalid_json(self) -> None:
        assert CategoryRouter._parse_categories("not json at all") == []

    def test_empty_array(self) -> None:
        assert CategoryRouter._parse_categories("[]") == []


class TestKeywordHints:
    """Tests for keyword-based category boosting."""

    @patch("business_assistant.agent.router.Agent")
    def test_keyword_hints_add_missing_category(self, mock_agent_cls) -> None:
        """AI returns 'web' but text contains 'email' — keyword hint adds 'email'."""
        registry = _make_registry()
        mock_result = MagicMock()
        mock_result.output = CategorySelection(categories=["web"])
        mock_result.usage.return_value = RunUsage()
        mock_agent_cls.return_value.run_sync.return_value = mock_result

        registry.register(
            PluginInfo(name="web_plugin", description="Web ops", category="web"),
            [Tool(lambda ctx: "ok", name="web_download")],
        )

        router = CategoryRouter(registry, model="openai:gpt-5-mini", model_name="gpt-5-mini")
        result = router.route("Do I have unread emails?")

        assert "email" in result.categories

    @patch("business_assistant.agent.router.Agent")
    def test_keyword_hints_no_match(self, mock_agent_cls) -> None:
        """Text without keywords does not add extra categories."""
        registry = _make_registry()
        mock_result = MagicMock()
        mock_result.output = CategorySelection(categories=[])
        mock_result.usage.return_value = RunUsage()
        mock_agent_cls.return_value.run_sync.return_value = mock_result

        router = CategoryRouter(registry, model="openai:gpt-5-mini", model_name="gpt-5-mini")
        result = router.route("hello, how are you?")

        assert result.categories == set()

    @patch("business_assistant.agent.router.Agent")
    def test_keyword_hints_german_keywords(self, mock_agent_cls) -> None:
        """German keyword 'Termine' maps to 'calendar'."""
        registry = _make_registry()
        mock_result = MagicMock()
        mock_result.output = CategorySelection(categories=[])
        mock_result.usage.return_value = RunUsage()
        mock_agent_cls.return_value.run_sync.return_value = mock_result

        router = CategoryRouter(registry, model="openai:gpt-5-mini", model_name="gpt-5-mini")
        result = router.route("Welche Termine habe ich heute?")

        assert "calendar" in result.categories

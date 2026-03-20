"""Tests for AIMessageHandler."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from bot_commander.types import BotMessage, BotResponse
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.usage import RunUsage

from business_assistant.agent.router import CategoryRouter, RoutingResult
from business_assistant.bot.handler import AIMessageHandler, _safe_truncate
from business_assistant.config.constants import (
    ERR_AGENT_FAILED,
    PLUGIN_DATA_COMMAND_HANDLERS,
    PLUGIN_DATA_MESSAGE_MODIFIERS,
    RESP_CHAT_CLEARED,
    RESP_RESTART_TRIGGERED,
    SYNONYM_PREFIX,
)
from business_assistant.files.downloader import FileDownloader
from business_assistant.memory.store import MemoryStore
from business_assistant.plugins.registry import PluginRegistry
from tests.conftest import make_test_settings


def _make_handler(
    agent_result: str = "Hello!",
    agent_error: Exception | None = None,
    tmp_memory_file: str = "",
    chat_log_file: str = "data/chat.log",
    chat_log_dir: str = "logs/chat",
    file_downloader: FileDownloader | None = None,
    plugin_data: dict | None = None,
) -> AIMessageHandler:
    """Create an AIMessageHandler with a mocked agent."""
    mock_agent = MagicMock()

    if agent_error:
        mock_agent.run_sync.side_effect = agent_error
    else:
        mock_result = MagicMock()
        mock_result.output = agent_result
        mock_result.all_messages.return_value = [{"role": "user"}, {"role": "assistant"}]
        mock_result.usage.return_value = RunUsage()
        mock_agent.run_sync.return_value = mock_result

    memory = MemoryStore(tmp_memory_file or "nonexistent.json")
    settings = make_test_settings(chat_log_file=chat_log_file, chat_log_dir=chat_log_dir)

    return AIMessageHandler(
        agent=mock_agent,
        memory=memory,
        settings=settings,
        file_downloader=file_downloader,
        plugin_data=plugin_data,
    )


class TestAIMessageHandler:
    def test_handle_success(self, tmp_memory_file: str) -> None:
        handler = _make_handler(agent_result="Hi there!", tmp_memory_file=tmp_memory_file)
        message = BotMessage(user_id="user@test.com", text="Hello")
        response = handler.handle(message)

        assert isinstance(response, BotResponse)
        assert response.text == "Hi there!"

    def test_handle_agent_error(self, tmp_memory_file: str) -> None:
        handler = _make_handler(
            agent_error=RuntimeError("boom"),
            tmp_memory_file=tmp_memory_file,
        )
        message = BotMessage(user_id="user@test.com", text="Hello")
        response = handler.handle(message)

        assert response.text == ERR_AGENT_FAILED


class TestConversationHistory:
    def test_history_passed_on_second_message(self, tmp_memory_file: str) -> None:
        handler = _make_handler(agent_result="Reply 1", tmp_memory_file=tmp_memory_file)

        handler.handle(BotMessage(user_id="user@test.com", text="First"))

        # First call should have empty history
        first_call = handler._agent.run_sync.call_args_list[0]
        assert first_call.kwargs["message_history"] == []

        handler.handle(BotMessage(user_id="user@test.com", text="Second"))

        # Second call should have history from first call
        second_call = handler._agent.run_sync.call_args_list[1]
        assert len(second_call.kwargs["message_history"]) == 2

    def test_separate_history_per_user(self, tmp_memory_file: str) -> None:
        handler = _make_handler(agent_result="Reply", tmp_memory_file=tmp_memory_file)

        handler.handle(BotMessage(user_id="alice@test.com", text="Hi from Alice"))
        handler.handle(BotMessage(user_id="bob@test.com", text="Hi from Bob"))

        # Bob's call should have empty history (Alice's history is separate)
        bob_call = handler._agent.run_sync.call_args_list[1]
        assert bob_call.kwargs["message_history"] == []

    def test_history_not_corrupted_on_error(self, tmp_memory_file: str) -> None:
        handler = _make_handler(agent_result="OK", tmp_memory_file=tmp_memory_file)

        # First message succeeds, builds history
        handler.handle(BotMessage(user_id="user@test.com", text="First"))
        assert "user@test.com" in handler._histories

        # Second message fails
        handler._agent.run_sync.side_effect = RuntimeError("boom")
        handler.handle(BotMessage(user_id="user@test.com", text="Second"))

        # History should still contain the first exchange
        assert len(handler._histories["user@test.com"]) == 2


class TestChatLogging:
    def test_chat_log_per_conversation_file_created(
        self, tmp_path: object, tmp_memory_file: str,
    ) -> None:
        log_dir = str(tmp_path / "chats")  # type: ignore[operator]
        handler = _make_handler(
            agent_result="Hi!",
            tmp_memory_file=tmp_memory_file,
            chat_log_dir=log_dir,
        )
        handler.handle(BotMessage(user_id="user@test.com", text="Hello"))

        # Find the JSONL file under the sanitized user directory
        user_dir = Path(log_dir) / "user_at_test.com"
        assert user_dir.exists()
        jsonl_files = list(user_dir.glob("*.jsonl"))
        assert len(jsonl_files) == 1

        with open(jsonl_files[0], encoding="utf-8") as f:
            entry = json.loads(f.readline())
        assert entry["user"] == "user@test.com"
        assert entry["in"] == "Hello"
        assert entry["out"] == "Hi!"
        assert entry["error"] is False
        assert "ts_in" in entry
        assert "ts_out" in entry
        assert isinstance(entry["duration_s"], float)
        assert isinstance(entry["tools_called"], list)
        assert isinstance(entry["llm_requests"], int)

    def test_chat_log_written_on_error(self, tmp_path: object, tmp_memory_file: str) -> None:
        log_dir = str(tmp_path / "chats")  # type: ignore[operator]
        handler = _make_handler(
            agent_error=RuntimeError("boom"),
            tmp_memory_file=tmp_memory_file,
            chat_log_dir=log_dir,
        )
        handler.handle(BotMessage(user_id="user@test.com", text="Hello"))

        user_dir = Path(log_dir) / "user_at_test.com"
        jsonl_files = list(user_dir.glob("*.jsonl"))
        assert len(jsonl_files) == 1

        with open(jsonl_files[0], encoding="utf-8") as f:
            entry = json.loads(f.readline())
        assert entry["user"] == "user@test.com"
        assert entry["in"] == "Hello"
        assert entry["out"] == ERR_AGENT_FAILED
        assert entry["error"] is True
        assert "ts_in" in entry
        assert "ts_out" in entry
        assert isinstance(entry["duration_s"], float)

    def test_chat_log_new_file_after_clear(
        self, tmp_path: object, tmp_memory_file: str,
    ) -> None:
        log_dir = str(tmp_path / "chats")  # type: ignore[operator]
        handler = _make_handler(
            agent_result="Hi!",
            tmp_memory_file=tmp_memory_file,
            chat_log_dir=log_dir,
        )

        handler.handle(BotMessage(user_id="user@test.com", text="Hello"))

        # Force a different timestamp for the next conversation
        handler._conversation_starts.pop("user@test.com")

        handler.handle(BotMessage(user_id="user@test.com", text="clear"))
        handler.handle(BotMessage(user_id="user@test.com", text="Hello again"))

        user_dir = Path(log_dir) / "user_at_test.com"
        jsonl_files = sorted(user_dir.glob("*.jsonl"))
        # May be 1 or 2 files depending on timestamp resolution;
        # verify at least two entries across files
        all_entries = []
        for f in jsonl_files:
            with open(f, encoding="utf-8") as fh:
                all_entries.extend(json.loads(line) for line in fh if line.strip())
        assert len(all_entries) == 2

    def test_chat_log_sanitizes_user_jid(
        self, tmp_path: object, tmp_memory_file: str,
    ) -> None:
        log_dir = str(tmp_path / "chats")  # type: ignore[operator]
        handler = _make_handler(
            agent_result="Hi!",
            tmp_memory_file=tmp_memory_file,
            chat_log_dir=log_dir,
        )
        handler.handle(BotMessage(user_id="user@test.com/resource", text="Hello"))

        # @ → _at_, / → _
        user_dir = Path(log_dir) / "user_at_test.com_resource"
        assert user_dir.exists()


class TestSafeTruncate:
    def test_no_truncation_needed(self) -> None:
        """Short history is returned unchanged."""
        history = [
            ModelRequest(parts=[UserPromptPart(content="hi")]),
            ModelResponse(parts=[TextPart(content="hello")]),
        ]
        result = _safe_truncate(history, max_len=10)
        assert result == history

    def test_truncation_at_safe_boundary(self) -> None:
        """When first message after truncation is a UserPromptPart, keep it."""
        history = [
            ModelRequest(parts=[UserPromptPart(content=f"msg-{i}")])
            for i in range(10)
        ]
        result = _safe_truncate(history, max_len=3)
        assert len(result) == 3
        assert isinstance(result[0], ModelRequest)
        assert isinstance(result[0].parts[0], UserPromptPart)

    def test_truncation_skips_orphaned_tool_return(self) -> None:
        """Orphaned ToolReturnPart messages at the start are skipped."""
        history = [
            # These will be before the truncation window
            ModelRequest(parts=[UserPromptPart(content="start")]),
            ModelResponse(parts=[ToolCallPart(tool_name="t", args={}, tool_call_id="1")]),
            # These will be in the truncation window
            ModelRequest(parts=[ToolReturnPart(tool_name="t", content="result", tool_call_id="1")]),
            ModelRequest(parts=[UserPromptPart(content="next question")]),
            ModelResponse(parts=[TextPart(content="answer")]),
        ]
        result = _safe_truncate(history, max_len=3)
        # Should skip the orphaned ToolReturnPart, keep the last 2
        assert len(result) == 2
        assert isinstance(result[0].parts[0], UserPromptPart)

    def test_truncation_skips_orphaned_retry_prompt(self) -> None:
        """Orphaned RetryPromptPart messages at the start are skipped."""
        history = [
            ModelRequest(parts=[UserPromptPart(content="start")]),
            ModelResponse(parts=[ToolCallPart(tool_name="t", args={}, tool_call_id="1")]),
            ModelRequest(parts=[RetryPromptPart(content="retry")]),
            ModelRequest(parts=[UserPromptPart(content="ok")]),
            ModelResponse(parts=[TextPart(content="done")]),
        ]
        result = _safe_truncate(history, max_len=3)
        assert len(result) == 2
        assert isinstance(result[0].parts[0], UserPromptPart)

    def test_all_tool_returns_gives_empty(self) -> None:
        """If all truncated messages are tool returns, return empty list."""
        history = [
            ModelRequest(parts=[UserPromptPart(content="old")]),
            ModelRequest(parts=[ToolReturnPart(tool_name="t", content="r", tool_call_id="1")]),
            ModelRequest(parts=[ToolReturnPart(tool_name="t", content="r", tool_call_id="2")]),
        ]
        result = _safe_truncate(history, max_len=2)
        assert result == []


class TestChatCommands:
    def test_clear_resets_history(self, tmp_memory_file: str) -> None:
        handler = _make_handler(agent_result="Reply", tmp_memory_file=tmp_memory_file)
        handler.handle(BotMessage(user_id="user@test.com", text="First"))
        assert "user@test.com" in handler._histories

        response = handler.handle(BotMessage(user_id="user@test.com", text="clear"))
        assert response.text == RESP_CHAT_CLEARED
        assert "user@test.com" not in handler._histories

    def test_clear_chat_history_variant(self, tmp_memory_file: str) -> None:
        handler = _make_handler(agent_result="Reply", tmp_memory_file=tmp_memory_file)
        handler.handle(BotMessage(user_id="user@test.com", text="First"))

        response = handler.handle(
            BotMessage(user_id="user@test.com", text="clear chat history")
        )
        assert response.text == RESP_CHAT_CLEARED

    def test_clear_is_case_insensitive(self, tmp_memory_file: str) -> None:
        handler = _make_handler(agent_result="Reply", tmp_memory_file=tmp_memory_file)
        handler.handle(BotMessage(user_id="user@test.com", text="First"))

        response = handler.handle(BotMessage(user_id="user@test.com", text="CLEAR"))
        assert response.text == RESP_CHAT_CLEARED

    def test_restart_creates_flag(self, tmp_path, tmp_memory_file: str) -> None:
        handler = _make_handler(tmp_memory_file=tmp_memory_file)
        flag = tmp_path / "restart.flag"

        import business_assistant.bot.handler as handler_mod

        orig = handler_mod.RESTART_FLAG_FILE
        handler_mod.RESTART_FLAG_FILE = str(flag)
        try:
            response = handler.handle(BotMessage(user_id="user@test.com", text="restart"))
            assert response.text == RESP_RESTART_TRIGGERED
            assert flag.exists()
        finally:
            handler_mod.RESTART_FLAG_FILE = orig
            flag.unlink(missing_ok=True)

    def test_restart_chat_variant(self, tmp_path, tmp_memory_file: str) -> None:
        handler = _make_handler(tmp_memory_file=tmp_memory_file)
        flag = tmp_path / "restart.flag"

        import business_assistant.bot.handler as handler_mod

        orig = handler_mod.RESTART_FLAG_FILE
        handler_mod.RESTART_FLAG_FILE = str(flag)
        try:
            response = handler.handle(
                BotMessage(user_id="user@test.com", text="restart chat")
            )
            assert response.text == RESP_RESTART_TRIGGERED
        finally:
            handler_mod.RESTART_FLAG_FILE = orig
            flag.unlink(missing_ok=True)

    def test_command_with_trailing_punctuation_matches(self, tmp_memory_file: str) -> None:
        """Trailing punctuation from transcription should not prevent command matching."""
        handler = _make_handler(agent_result="Reply", tmp_memory_file=tmp_memory_file)
        handler.handle(BotMessage(user_id="user@test.com", text="First"))

        response = handler.handle(BotMessage(user_id="user@test.com", text="clear."))
        assert response.text == RESP_CHAT_CLEARED
        assert "user@test.com" not in handler._histories

    def test_normal_message_not_intercepted(self, tmp_memory_file: str) -> None:
        handler = _make_handler(agent_result="Hi!", tmp_memory_file=tmp_memory_file)
        response = handler.handle(BotMessage(user_id="user@test.com", text="hello"))
        assert response.text == "Hi!"
        handler._agent.run_sync.assert_called_once()


class TestStickyCategories:
    def _make_routed_handler(
        self,
        tmp_memory_file: str,
        tmp_path: Path,
        route_results: list[set[str]],
    ) -> AIMessageHandler:
        """Create a handler with mocked router and registry."""
        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.output = "OK"
        mock_result.all_messages.return_value = [{"role": "user"}, {"role": "assistant"}]
        mock_result.usage.return_value = RunUsage()
        mock_agent.run_sync.return_value = mock_result

        mock_router = MagicMock(spec=CategoryRouter)
        call_idx = {"i": 0}

        def _route(text: str) -> RoutingResult:
            idx = min(call_idx["i"], len(route_results) - 1)
            call_idx["i"] += 1
            return RoutingResult(categories=route_results[idx], usage=None)

        mock_router.route.side_effect = _route

        mock_registry = MagicMock(spec=PluginRegistry)
        mock_registry.tools_for_categories.return_value = []
        mock_registry.prompts_for_categories.return_value = ""

        memory = MemoryStore(tmp_memory_file)
        log_dir = str(tmp_path / "chats")
        settings = make_test_settings(chat_log_dir=log_dir)

        return AIMessageHandler(
            agent=mock_agent,
            memory=memory,
            settings=settings,
            registry=mock_registry,
            router=mock_router,
            core_tools=[],
        )

    def test_categories_sticky_across_turns(
        self, tmp_memory_file: str, tmp_path: Path,
    ) -> None:
        """Second turn should include categories from the first turn."""
        handler = self._make_routed_handler(
            tmp_memory_file, tmp_path,
            route_results=[{"todo"}, set()],
        )

        handler.handle(BotMessage(user_id="user@test.com", text="Add task"))
        handler.handle(BotMessage(user_id="user@test.com", text="Ja"))

        # Second call to tools_for_categories should include "todo" from stickiness
        calls = handler._registry.tools_for_categories.call_args_list  # type: ignore[union-attr]
        assert calls[0].args[0] == {"todo"}
        assert "todo" in calls[1].args[0]

    def test_clear_resets_sticky_categories(
        self, tmp_memory_file: str, tmp_path: Path,
    ) -> None:
        """Clear command should reset sticky categories."""
        handler = self._make_routed_handler(
            tmp_memory_file, tmp_path,
            route_results=[{"todo"}, set()],
        )

        handler.handle(BotMessage(user_id="user@test.com", text="Add task"))
        assert "user@test.com" in handler._last_categories

        handler.handle(BotMessage(user_id="user@test.com", text="clear"))
        assert "user@test.com" not in handler._last_categories

        handler.handle(BotMessage(user_id="user@test.com", text="Ja"))

        # After clear, second routed call should have empty categories only
        calls = handler._registry.tools_for_categories.call_args_list  # type: ignore[union-attr]
        assert calls[1].args[0] == set()


class TestChatLogModifiedText:
    def test_chat_log_records_modified_text(
        self, tmp_path: Path, tmp_memory_file: str,
    ) -> None:
        """Chat log should record the modified/transcribed text, not the raw input."""
        log_dir = str(tmp_path / "chats")

        def _modifier(text: str, user_id: str, plugin_data: dict) -> str:
            return text.replace("raw_url", "transcribed text")

        handler = _make_handler(
            agent_result="Got it!",
            tmp_memory_file=tmp_memory_file,
            chat_log_dir=log_dir,
            plugin_data={PLUGIN_DATA_MESSAGE_MODIFIERS: [_modifier]},
        )
        handler.handle(BotMessage(user_id="user@test.com", text="raw_url"))

        user_dir = Path(log_dir) / "user_at_test.com"
        jsonl_files = list(user_dir.glob("*.jsonl"))
        with open(jsonl_files[0], encoding="utf-8") as f:
            entry = json.loads(f.readline())
        assert entry["in"] == "transcribed text"


class TestSynonymResolution:
    def test_synonym_resolves_to_builtin_command(self, tmp_memory_file: str) -> None:
        """A synonym mapping to 'clear' should trigger the clear command."""
        handler = _make_handler(agent_result="Reply", tmp_memory_file=tmp_memory_file)
        handler._memory.set(f"{SYNONYM_PREFIX}löschen", "clear")
        handler.handle(BotMessage(user_id="user@test.com", text="First"))

        response = handler.handle(BotMessage(user_id="user@test.com", text="löschen"))
        assert response.text == RESP_CHAT_CLEARED
        assert "user@test.com" not in handler._histories

    def test_synonym_resolves_to_plugin_command(self, tmp_memory_file: str) -> None:
        """A synonym should resolve and be checked against plugin command handlers."""
        def _plugin_handler(text: str, user_id: str, plugin_data: dict) -> BotResponse | None:
            if text.lower().strip() == "my plugin cmd":
                return BotResponse(text="Plugin handled!")
            return None

        handler = _make_handler(
            agent_result="AI reply",
            tmp_memory_file=tmp_memory_file,
            plugin_data={PLUGIN_DATA_COMMAND_HANDLERS: [_plugin_handler]},
        )
        handler._memory.set(f"{SYNONYM_PREFIX}shortcut", "my plugin cmd")

        response = handler.handle(BotMessage(user_id="user@test.com", text="shortcut"))
        assert response.text == "Plugin handled!"

    def test_synonym_case_insensitive(self, tmp_memory_file: str) -> None:
        """Synonym lookup should be case-insensitive."""
        handler = _make_handler(agent_result="Reply", tmp_memory_file=tmp_memory_file)
        handler._memory.set(f"{SYNONYM_PREFIX}löschen", "clear")

        response = handler.handle(BotMessage(user_id="user@test.com", text="LÖSCHEN"))
        assert response.text == RESP_CHAT_CLEARED

    def test_synonym_with_trailing_punctuation(self, tmp_memory_file: str) -> None:
        """Trailing punctuation should be stripped before synonym lookup."""
        handler = _make_handler(agent_result="Reply", tmp_memory_file=tmp_memory_file)
        handler._memory.set(f"{SYNONYM_PREFIX}löschen", "clear")
        handler.handle(BotMessage(user_id="user@test.com", text="First"))

        response = handler.handle(BotMessage(user_id="user@test.com", text="löschen."))
        assert response.text == RESP_CHAT_CLEARED
        assert "user@test.com" not in handler._histories

    def test_unknown_word_passes_through(self, tmp_memory_file: str) -> None:
        """A word that is not a synonym should pass through to the AI agent."""
        handler = _make_handler(agent_result="AI reply", tmp_memory_file=tmp_memory_file)

        response = handler.handle(BotMessage(user_id="user@test.com", text="unknown"))
        assert response.text == "AI reply"
        handler._agent.run_sync.assert_called_once()

    def test_no_recursive_resolution(self, tmp_memory_file: str) -> None:
        """Synonyms should not chain — only one level of resolution."""
        handler = _make_handler(agent_result="AI reply", tmp_memory_file=tmp_memory_file)
        handler._memory.set(f"{SYNONYM_PREFIX}a", "b")
        handler._memory.set(f"{SYNONYM_PREFIX}b", "clear")

        # "a" resolves to "b", but "b" should NOT further resolve to "clear"
        response = handler.handle(BotMessage(user_id="user@test.com", text="a"))
        assert response.text == "AI reply"
        handler._agent.run_sync.assert_called_once()


class TestContextLimitWarning:
    @staticmethod
    def _make_handler_with_limit(
        tmp_memory_file: str,
        threshold: int,
        input_tokens: int = 50000,
    ) -> AIMessageHandler:
        """Create a handler with context limit and controllable input_tokens."""
        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.output = "OK"
        mock_result.all_messages.return_value = [{"role": "user"}, {"role": "assistant"}]
        mock_result.usage.return_value = RunUsage(input_tokens=input_tokens)
        mock_agent.run_sync.return_value = mock_result

        memory = MemoryStore(tmp_memory_file)
        settings = make_test_settings(context_limit_threshold=threshold)

        return AIMessageHandler(
            agent=mock_agent,
            memory=memory,
            settings=settings,
        )

    def test_warning_appended_when_over_limit(self, tmp_memory_file: str) -> None:
        handler = self._make_handler_with_limit(
            tmp_memory_file, threshold=30000, input_tokens=35000,
        )
        response = handler.handle(BotMessage(user_id="user@test.com", text="Hello"))
        assert "35000 input tokens" in response.text
        assert "clear" in response.text

    def test_warning_only_once(self, tmp_memory_file: str) -> None:
        handler = self._make_handler_with_limit(
            tmp_memory_file, threshold=30000, input_tokens=35000,
        )
        r1 = handler.handle(BotMessage(user_id="user@test.com", text="Hello"))
        assert "input tokens" in r1.text

        r2 = handler.handle(BotMessage(user_id="user@test.com", text="Again"))
        assert "input tokens" not in r2.text

    def test_warning_resets_after_clear(self, tmp_memory_file: str) -> None:
        handler = self._make_handler_with_limit(
            tmp_memory_file, threshold=30000, input_tokens=35000,
        )
        handler.handle(BotMessage(user_id="user@test.com", text="Hello"))
        handler.handle(BotMessage(user_id="user@test.com", text="clear"))
        r3 = handler.handle(BotMessage(user_id="user@test.com", text="Hello again"))
        assert "input tokens" in r3.text

    def test_no_warning_when_under_limit(self, tmp_memory_file: str) -> None:
        handler = self._make_handler_with_limit(
            tmp_memory_file, threshold=30000, input_tokens=10000,
        )
        response = handler.handle(BotMessage(user_id="user@test.com", text="Hello"))
        assert response.text == "OK"

    def test_no_warning_when_disabled(self, tmp_memory_file: str) -> None:
        handler = self._make_handler_with_limit(
            tmp_memory_file, threshold=0, input_tokens=50000,
        )
        response = handler.handle(BotMessage(user_id="user@test.com", text="Hello"))
        assert response.text == "OK"


class TestRouterFailureUsageTracking:
    def test_router_failure_returns_error_and_logs_usage(
        self, tmp_memory_file: str, tmp_path: Path,
    ) -> None:
        """When the router fails, user gets error message and usage is logged."""
        mock_agent = MagicMock()

        mock_router = MagicMock(spec=CategoryRouter)
        mock_router.route.return_value = RoutingResult(
            categories=set(), usage=RunUsage(requests=1), failed=True,
        )
        mock_router.model_name = "qwen2.5:1.5b"

        mock_registry = MagicMock(spec=PluginRegistry)

        mock_tracker = MagicMock()

        memory = MemoryStore(tmp_memory_file)
        log_dir = str(tmp_path / "chats")
        settings = make_test_settings(chat_log_dir=log_dir)

        handler = AIMessageHandler(
            agent=mock_agent,
            memory=memory,
            settings=settings,
            registry=mock_registry,
            router=mock_router,
            core_tools=[],
            usage_tracker=mock_tracker,
            model_name="deepseek-chat",
            provider="custom",
            router_provider="ollama",
        )

        response = handler.handle(BotMessage(user_id="user@test.com", text="Hello"))

        # User should get the router error message
        assert "router model failed" in response.text.lower()
        # Agent should NOT have been called
        mock_agent.run_sync.assert_not_called()
        # Router usage should still be logged
        mock_tracker.log.assert_called_once()
        router_call = mock_tracker.log.call_args
        assert router_call.args[3] == "qwen2.5:1.5b"
        assert router_call.kwargs["provider"] == "ollama"
        assert router_call.args[0].requests == 1


class TestFailedRequestUsageTracking:
    def test_agent_failure_logs_usage(self, tmp_memory_file: str) -> None:
        """When the agent fails, the failed attempt should still be logged."""
        mock_agent = MagicMock()
        mock_agent.run_sync.side_effect = RuntimeError("API timeout")

        mock_tracker = MagicMock()
        memory = MemoryStore(tmp_memory_file)
        settings = make_test_settings()

        handler = AIMessageHandler(
            agent=mock_agent,
            memory=memory,
            settings=settings,
            usage_tracker=mock_tracker,
            model_name="deepseek-chat",
            provider="custom",
        )

        response = handler.handle(BotMessage(user_id="user@test.com", text="Hello"))
        assert response.text == ERR_AGENT_FAILED

        mock_tracker.log.assert_called_once()
        call_args = mock_tracker.log.call_args
        usage = call_args.args[0]
        assert usage.requests == 1
        assert usage.input_tokens == 0
        assert call_args.args[2] == "user@test.com"
        assert call_args.args[3] == "deepseek-chat"
        assert call_args.kwargs["provider"] == "custom"



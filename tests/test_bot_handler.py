"""Tests for AIMessageHandler."""

from __future__ import annotations

import json
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

from business_assistant.bot.handler import AIMessageHandler, _safe_truncate
from business_assistant.config.constants import (
    ERR_AGENT_FAILED,
    RESP_CHAT_CLEARED,
    RESP_RESTART_TRIGGERED,
)
from business_assistant.config.settings import AppSettings, OpenAISettings, XmppSettings
from business_assistant.memory.store import MemoryStore


def _make_handler(
    agent_result: str = "Hello!",
    agent_error: Exception | None = None,
    tmp_memory_file: str = "",
    chat_log_file: str = "data/chat.log",
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
    settings = AppSettings(
        xmpp=XmppSettings(
            jid="bot@test.com",
            password="pass",
            default_receiver="user@test.com",
            allowed_jids=["user@test.com"],
        ),
        openai=OpenAISettings(api_key="sk-test", model="gpt-4o"),
        memory_file="data/memory.json",
        chat_log_file=chat_log_file,
        usage_log_file="data/usage.log",
        plugin_names=[],
    )

    return AIMessageHandler(
        agent=mock_agent,
        memory=memory,
        settings=settings,
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
    def test_chat_log_written_on_success(self, tmp_path: object, tmp_memory_file: str) -> None:
        log_file = str(tmp_path / "chat.log")  # type: ignore[operator]
        handler = _make_handler(
            agent_result="Hi!", tmp_memory_file=tmp_memory_file, chat_log_file=log_file
        )
        handler.handle(BotMessage(user_id="user@test.com", text="Hello"))

        with open(log_file, encoding="utf-8") as f:
            entry = json.loads(f.readline())
        assert entry["user"] == "user@test.com"
        assert entry["in"] == "Hello"
        assert entry["out"] == "Hi!"
        assert entry["error"] is False
        assert "ts" in entry

    def test_chat_log_written_on_error(self, tmp_path: object, tmp_memory_file: str) -> None:
        log_file = str(tmp_path / "chat.log")  # type: ignore[operator]
        handler = _make_handler(
            agent_error=RuntimeError("boom"),
            tmp_memory_file=tmp_memory_file,
            chat_log_file=log_file,
        )
        handler.handle(BotMessage(user_id="user@test.com", text="Hello"))

        with open(log_file, encoding="utf-8") as f:
            entry = json.loads(f.readline())
        assert entry["user"] == "user@test.com"
        assert entry["in"] == "Hello"
        assert entry["out"] == ERR_AGENT_FAILED
        assert entry["error"] is True


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

    def test_normal_message_not_intercepted(self, tmp_memory_file: str) -> None:
        handler = _make_handler(agent_result="Hi!", tmp_memory_file=tmp_memory_file)
        response = handler.handle(BotMessage(user_id="user@test.com", text="hello"))
        assert response.text == "Hi!"
        handler._agent.run_sync.assert_called_once()

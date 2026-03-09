"""AIMessageHandler — routes XMPP messages to PydanticAI agent."""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from bot_commander.types import BotMessage, BotResponse
from pydantic_ai import Agent
from pydantic_ai.messages import ModelRequest, RetryPromptPart, ToolReturnPart

from business_assistant.agent.deps import Deps
from business_assistant.config.constants import (
    ERR_AGENT_FAILED,
    LOG_AGENT_ERROR,
)
from business_assistant.config.settings import AppSettings
from business_assistant.memory.store import MemoryStore

logger = logging.getLogger(__name__)


class AIMessageHandler:
    """Implements the MessageHandler protocol from bot-commander.

    Routes all incoming messages to the PydanticAI agent using a
    ThreadPoolExecutor to avoid blocking the XMPP async event loop.
    Maintains per-user conversation history for multi-turn context.
    """

    def __init__(
        self,
        agent: Agent[Deps, str],
        memory: MemoryStore,
        settings: AppSettings,
        plugin_data: dict | None = None,
    ) -> None:
        self._agent = agent
        self._memory = memory
        self._settings = settings
        self._plugin_data = plugin_data or {}
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._chat_log_path = Path(settings.chat_log_file)
        self._chat_log_path.parent.mkdir(parents=True, exist_ok=True)
        self._histories: dict[str, list] = {}

    def handle(self, message: BotMessage) -> BotResponse:
        """Handle an incoming bot message by routing to the AI agent.

        Runs agent.run_sync() in a separate thread to avoid event loop conflicts.
        """
        try:
            deps = Deps(
                memory=self._memory,
                settings=self._settings,
                user_id=message.user_id,
                plugin_data=self._plugin_data,
            )
            history = self._histories.get(message.user_id, [])
            future = self._executor.submit(
                self._run_agent,
                message.text,
                deps,
                history,
            )
            output, new_history = future.result(timeout=120)
            self._histories[message.user_id] = _safe_truncate(
                new_history, self._settings.max_conversation_history
            )
            self._log_chat(message.user_id, message.text, output, error=False)
            return BotResponse(text=output)
        except Exception:
            logger.error(LOG_AGENT_ERROR, exc_info=True)
            self._log_chat(message.user_id, message.text, ERR_AGENT_FAILED, error=True)
            return BotResponse(text=ERR_AGENT_FAILED)

    def _run_agent(self, text: str, deps: Deps, message_history: list) -> tuple[str, list]:
        """Run the PydanticAI agent synchronously (called from thread pool)."""
        result = self._agent.run_sync(text, deps=deps, message_history=message_history)
        return result.output, result.all_messages()

    def _log_chat(self, user: str, input_text: str, output_text: str, *, error: bool) -> None:
        """Append a JSON line to the chat log file."""
        try:
            entry = {
                "ts": datetime.now(tz=UTC).isoformat(),
                "user": user,
                "in": input_text,
                "out": output_text,
                "error": error,
            }
            with open(self._chat_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            logger.warning("Failed to write chat log entry", exc_info=True)


def _safe_truncate(
    history: list,
    max_len: int,
) -> list:
    """Truncate history without breaking tool call/response pairs.

    A naive slice can start with a ModelRequest containing ToolReturnPart or
    RetryPromptPart, which OpenAI rejects because those require a preceding
    ModelResponse with a ToolCallPart.  This function skips past any such
    orphaned messages at the start of the truncated window.
    """
    if len(history) <= max_len:
        return history
    truncated = history[-max_len:]
    start = 0
    for i, msg in enumerate(truncated):
        if isinstance(msg, ModelRequest) and msg.parts and isinstance(
            msg.parts[0], (ToolReturnPart, RetryPromptPart)
        ):
            start = i + 1
        else:
            break
    return truncated[start:]

"""AIMessageHandler — routes XMPP messages to PydanticAI agent."""

from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from bot_commander.types import BotMessage, BotResponse
from pydantic_ai import Agent
from pydantic_ai.messages import ModelRequest, RetryPromptPart, ToolReturnPart
from pydantic_ai.usage import RunUsage

from business_assistant.agent.deps import Deps
from business_assistant.agent.router import CategoryRouter
from business_assistant.config.constants import (
    CMD_CLEAR,
    CMD_RESTART,
    ERR_AGENT_FAILED,
    LOG_AGENT_ERROR,
    LOG_STICKY_CATEGORIES,
    LOG_TOOLS_SELECTED,
    OPENAI_MAX_TOOLS,
    PLUGIN_DATA_COMMAND_HANDLERS,
    PLUGIN_DATA_FILE_HANDLERS,
    PLUGIN_DATA_MESSAGE_MODIFIERS,
    PLUGIN_DATA_RESPONSE_PROCESSORS,
    RESP_CHAT_CLEARED,
    RESP_RESTART_TRIGGERED,
    RESTART_FLAG_FILE,
    SYNONYM_PREFIX,
    TRANSCRIPTION_PREFIX,
)
from business_assistant.config.settings import AppSettings
from business_assistant.files.downloader import FileDownloader
from business_assistant.memory.store import MemoryStore
from business_assistant.plugins.registry import PluginRegistry
from business_assistant.usage.tracker import UsageTracker

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
        usage_tracker: UsageTracker | None = None,
        model_name: str = "",
        file_downloader: FileDownloader | None = None,
        registry: PluginRegistry | None = None,
        router: CategoryRouter | None = None,
        core_tools: list | None = None,
    ) -> None:
        self._agent = agent
        self._memory = memory
        self._settings = settings
        self._plugin_data = plugin_data or {}
        self._usage_tracker = usage_tracker
        self._model_name = model_name
        self._file_downloader = file_downloader
        self._registry = registry
        self._router = router
        self._core_tools = core_tools or []
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._chat_log_dir = Path(settings.chat_log_dir)
        self._chat_log_dir.mkdir(parents=True, exist_ok=True)
        self._conversation_starts: dict[str, str] = {}
        self._last_categories: dict[str, set[str]] = {}
        self._histories: dict[str, list] = {}

    def handle(self, message: BotMessage) -> BotResponse:
        """Handle an incoming bot message by routing to the AI agent.

        Runs agent.run_sync() in a separate thread to avoid event loop conflicts.
        """
        cmd_response = self._handle_command(message.text.strip(), message.user_id)
        if cmd_response is not None:
            return cmd_response

        try:
            file_prefix, transcriptions = self._process_attachments(message)

            # Voice-only message: check if transcription matches a command
            if not message.text.strip() and transcriptions:
                for transcription in transcriptions:
                    cmd_response = self._handle_command(
                        transcription, message.user_id,
                    )
                    if cmd_response is not None:
                        return cmd_response

            agent_text = file_prefix + message.text if file_prefix else message.text
            agent_text = self._apply_message_modifiers(agent_text, message.user_id)

            deps = Deps(
                memory=self._memory,
                settings=self._settings,
                user_id=message.user_id,
                plugin_data=self._plugin_data,
            )
            history = self._histories.get(message.user_id, [])
            future = self._executor.submit(
                self._run_agent,
                agent_text,
                deps,
                history,
                message.user_id,
            )
            output, new_history, usage = future.result(timeout=120)
            self._histories[message.user_id] = _safe_truncate(
                new_history, self._settings.max_conversation_history
            )
            self._log_chat(message.user_id, agent_text, output, error=False)
            if self._usage_tracker:
                self._usage_tracker.log(
                    usage, new_history, message.user_id, self._model_name
                )
            response = BotResponse(text=output)
            response = self._apply_response_processors(response, message.user_id)
            return response
        except Exception:
            logger.error(LOG_AGENT_ERROR, exc_info=True)
            self._log_chat(message.user_id, agent_text, ERR_AGENT_FAILED, error=True)
            return BotResponse(text=ERR_AGENT_FAILED)

    def _apply_message_modifiers(self, text: str, user_id: str) -> str:
        """Apply registered message modifiers to transform text before AI."""
        for modifier in self._plugin_data.get(PLUGIN_DATA_MESSAGE_MODIFIERS, []):
            try:
                text = modifier(text, user_id, self._plugin_data)
            except Exception:
                logger.warning("Message modifier failed", exc_info=True)
        return text

    def _apply_response_processors(
        self, response: BotResponse, user_id: str
    ) -> BotResponse:
        """Apply registered response processors to transform the response."""
        processors = self._plugin_data.get(PLUGIN_DATA_RESPONSE_PROCESSORS, [])
        for processor in processors:
            try:
                response = processor(response, user_id, self._plugin_data)
            except Exception:
                logger.warning("Response processor failed", exc_info=True)
        return response

    def _process_attachments(
        self, message: BotMessage,
    ) -> tuple[str, list[str]]:
        """Download attachments and run file handlers.

        Returns (context_prefix, transcriptions) where *transcriptions* is a
        list of raw transcription texts extracted from file handler results.
        """
        if not message.attachments or not self._file_downloader:
            return "", []

        from business_assistant.files.handler_registry import FileHandlerRegistry

        parts: list[str] = []
        transcriptions: list[str] = []
        handler_registry: FileHandlerRegistry | None = self._plugin_data.get(
            PLUGIN_DATA_FILE_HANDLERS
        )

        for att in message.attachments:
            try:
                downloaded = self._file_downloader.download(
                    att.url, att.filename, att.mime_type
                )
                parts.append(
                    f"[File received: {downloaded.filename} "
                    f"({downloaded.mime_type or 'unknown'}, {downloaded.size} bytes) "
                    f"saved to {downloaded.path}]"
                )
                if handler_registry and downloaded.mime_type:
                    for plugin_name, handler_fn in handler_registry.get_handlers(
                        downloaded.mime_type
                    ):
                        try:
                            result = handler_fn(downloaded, message.user_id)
                            parts.append(
                                f"[File processed by {plugin_name}: {result.summary}]"
                            )
                            if result.summary.startswith(TRANSCRIPTION_PREFIX):
                                transcriptions.append(
                                    result.summary[len(TRANSCRIPTION_PREFIX):]
                                )
                        except Exception:
                            logger.warning(
                                "File handler %s failed", plugin_name, exc_info=True
                            )
            except Exception:
                logger.warning("Failed to download attachment: %s", att.url, exc_info=True)

        if parts:
            return "\n".join(parts) + "\n", transcriptions
        return "", transcriptions

    def _run_agent(
        self,
        text: str,
        deps: Deps,
        message_history: list,
        user_id: str = "",
    ) -> tuple[str, list, RunUsage]:
        """Run the PydanticAI agent synchronously (called from thread pool).

        Routing and agent execution both run here (in the thread pool)
        to avoid event loop conflicts with the XMPP async loop.
        """
        tools, instructions = self._select_tools(text, user_id)

        if tools is not None:
            override_kwargs: dict = {"tools": tools}
            if instructions is not None:
                override_kwargs["instructions"] = instructions
            with self._agent.override(**override_kwargs):
                result = self._agent.run_sync(
                    text, deps=deps, message_history=message_history,
                )
        else:
            result = self._agent.run_sync(
                text, deps=deps, message_history=message_history,
            )
        return result.output, result.all_messages(), result.usage()

    def _select_tools(
        self, text: str, user_id: str,
    ) -> tuple[list | None, str | None]:
        """Route message to plugin categories and return selected tools.

        Called from thread pool to avoid event loop conflicts.
        Returns (tools, instructions) or (None, None) if no router configured.
        """
        if not self._router or not self._registry:
            return None, None

        routing_result = self._router.route(text)

        # Track router usage
        if self._usage_tracker and routing_result.usage:
            self._usage_tracker.log(
                routing_result.usage, [],
                user_id, self._router.model_name,
            )

        # Merge with previously-used categories for this user (sticky)
        merged = routing_result.categories | self._last_categories.get(user_id, set())
        if merged != routing_result.categories:
            logger.info(LOG_STICKY_CATEGORIES, user_id, merged - routing_result.categories)
        self._last_categories[user_id] = merged

        category_tools = self._registry.tools_for_categories(merged)
        selected_tools = list(self._core_tools) + category_tools

        # Guard: ensure we don't exceed OpenAI tool limit
        if len(selected_tools) >= OPENAI_MAX_TOOLS:
            logger.warning(
                "Categories %s yield %d tools (limit %d), "
                "falling back to core only",
                routing_result.categories,
                len(selected_tools),
                OPENAI_MAX_TOOLS,
            )
            return list(self._core_tools), ""

        tool_names = [
            getattr(t, "__name__", None) or getattr(t, "name", str(t))
            for t in selected_tools
        ]
        logger.info(
            LOG_TOOLS_SELECTED,
            user_id,
            merged,
            tool_names,
        )
        instructions = self._registry.prompts_for_categories(merged)
        return selected_tools, instructions

    def _handle_command(self, text: str, user_id: str) -> BotResponse | None:
        """Check for special chat commands. Returns a BotResponse or None."""
        normalized = text.lower().strip().rstrip(".,!?;:")
        text = text.strip().rstrip(".,!?;:")
        synonym_target = self._memory.get(f"{SYNONYM_PREFIX}{normalized}")
        if synonym_target is not None:
            normalized = synonym_target.lower().strip()
            text = normalized
        if normalized in CMD_CLEAR:
            self._histories.pop(user_id, None)
            self._conversation_starts.pop(user_id, None)
            self._last_categories.pop(user_id, None)
            logger.info("Chat history cleared for user %s", user_id)
            return BotResponse(text=RESP_CHAT_CLEARED)
        if normalized in CMD_RESTART:
            Path(RESTART_FLAG_FILE).touch()
            logger.info("Restart requested by user %s", user_id)
            return BotResponse(text=RESP_RESTART_TRIGGERED)

        for handler in self._plugin_data.get(PLUGIN_DATA_COMMAND_HANDLERS, []):
            try:
                result = handler(text, user_id, self._plugin_data)
                if result is not None:
                    return result
            except Exception:
                logger.warning("Plugin command handler failed", exc_info=True)

        return None

    def _get_chat_log_path(self, user: str) -> Path:
        """Return the per-conversation JSONL log path for a user.

        Creates parent directories on first call. A new conversation file
        is started when the user has no entry in ``_conversation_starts``
        (i.e. on handler init or after a "clear" command).
        """
        if user not in self._conversation_starts:
            self._conversation_starts[user] = datetime.now(tz=UTC).strftime(
                "%Y-%m-%d_%H-%M-%S"
            )
        sanitized = re.sub(r"[^\w.\-]", "_", user.replace("@", "_at_"))
        log_path = (
            self._chat_log_dir / sanitized / f"{self._conversation_starts[user]}.jsonl"
        )
        log_path.parent.mkdir(parents=True, exist_ok=True)
        return log_path

    def _log_chat(self, user: str, input_text: str, output_text: str, *, error: bool) -> None:
        """Append a JSON line to the per-conversation chat log file."""
        try:
            entry = {
                "ts": datetime.now(tz=UTC).isoformat(),
                "user": user,
                "in": input_text,
                "out": output_text,
                "error": error,
            }
            log_path = self._get_chat_log_path(user)
            with open(log_path, "a", encoding="utf-8") as f:
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

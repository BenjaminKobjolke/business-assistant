"""Usage tracker — logs OpenAI API token consumption per agent run as JSONL."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.usage import RunUsage

from business_assistant.config.constants import CORE_PLUGIN_NAME

logger = logging.getLogger(__name__)


class UsageTracker:
    """Appends per-run token usage records to a JSONL file."""

    def __init__(self, file_path: str, tool_plugin_map: dict[str, str]) -> None:
        self._path = Path(file_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._tool_plugin_map = dict(tool_plugin_map)

    def log(
        self,
        usage: RunUsage,
        messages: list[Any],
        user: str,
        model: str,
    ) -> None:
        """Extract tool info from messages and append a usage record."""
        try:
            tools_called = self._extract_tool_names(messages)
            plugins = list(dict.fromkeys(
                self._tool_plugin_map.get(t, CORE_PLUGIN_NAME) for t in tools_called
            ))

            entry = {
                "ts": datetime.now(tz=UTC).isoformat(),
                "user": user,
                "model": model,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cache_read_tokens": usage.cache_read_tokens,
                "cache_write_tokens": usage.cache_write_tokens,
                "requests": usage.requests,
                "tool_calls_count": usage.tool_calls,
                "tools_called": tools_called,
                "plugins_involved": plugins,
            }
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            logger.warning("Failed to write usage log entry", exc_info=True)

    @staticmethod
    def _extract_tool_names(messages: list[Any]) -> list[str]:
        """Return deduplicated tool names from ModelResponse messages."""
        seen: dict[str, None] = {}
        for msg in messages:
            if isinstance(msg, ModelResponse):
                for part in msg.parts:
                    if isinstance(part, ToolCallPart):
                        seen.setdefault(part.tool_name, None)
        return list(seen)

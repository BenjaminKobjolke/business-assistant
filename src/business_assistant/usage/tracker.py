"""Usage tracker — logs OpenAI API token consumption per agent run as daily JSONL files."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.usage import RunUsage

from business_assistant.config.constants import (
    CORE_PLUGIN_NAME,
    USAGE_LOG_PREFIX,
    USAGE_LOG_SUFFIX,
    USAGE_SOURCE_BOT,
)

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _resolve_root(log_dir: str) -> Path:
    """Resolve a potentially relative log_dir against the project root."""
    p = Path(log_dir)
    if p.is_absolute():
        return p
    return _PROJECT_ROOT / p


class UsageTracker:
    """Appends per-run token usage records to daily JSONL files."""

    def __init__(self, log_dir: str, tool_plugin_map: dict[str, str]) -> None:
        self._log_dir = _resolve_root(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._tool_plugin_map = dict(tool_plugin_map)

    def _resolve_path(self, ts: datetime) -> Path:
        """Compute the log file path for a given timestamp."""
        date_str = ts.strftime("%Y-%m-%d")
        filename = f"{USAGE_LOG_PREFIX}.{date_str}{USAGE_LOG_SUFFIX}"
        return self._log_dir / filename

    def log(
        self,
        usage: RunUsage,
        messages: list[Any],
        user: str,
        model: str,
        source: str = USAGE_SOURCE_BOT,
        provider: str = "",
    ) -> None:
        """Extract tool info from messages and append a usage record."""
        try:
            now = datetime.now(tz=UTC)
            tools_called = self._extract_tool_names(messages)
            plugins = list(dict.fromkeys(
                self._tool_plugin_map.get(t, CORE_PLUGIN_NAME) for t in tools_called
            ))

            entry: dict[str, Any] = {
                "ts": now.isoformat(),
                "source": source,
                "user": user,
                "model": model,
                "provider": provider,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cache_read_tokens": usage.cache_read_tokens,
                "cache_write_tokens": usage.cache_write_tokens,
                "requests": usage.requests,
                "tool_calls_count": usage.tool_calls,
                "tools_called": tools_called,
                "plugins_involved": plugins,
            }
            path = self._resolve_path(now)
            with open(path, "a", encoding="utf-8") as f:
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

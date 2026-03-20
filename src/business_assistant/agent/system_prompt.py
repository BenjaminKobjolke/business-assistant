"""System prompt builder for the PydanticAI agent."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from business_assistant.config.constants import SYSTEM_PROMPT_BASE
from business_assistant.memory.store import MemoryStore
from business_assistant.plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)


def build_system_prompt(
    registry: PluginRegistry,
    memory: MemoryStore,
    include_plugins: bool = True,
) -> str:
    """Build the system prompt from base template, memory, and optionally plugin extras.

    Args:
        registry: Plugin registry.
        memory: Memory store.
        include_plugins: If False, omit plugin extras (they'll be injected per-request).
    """
    plugin_extras = registry.system_prompt_extras() if include_plugins else ""
    return SYSTEM_PROMPT_BASE.format(
        memory_contents=memory.format_contents(),
        plugin_extras=plugin_extras,
    )


def build_time_prompt(timezone: str) -> str:
    """Return a line with the current local date, time, and timezone.

    Called dynamically on each agent run so the value is always fresh.
    """
    utc_now = datetime.now(tz=UTC)
    tz = ZoneInfo(timezone)
    now = utc_now.astimezone(tz)
    local_str = now.strftime("%Y-%m-%d %H:%M:%S %Z")
    utc_str = utc_now.strftime("%Y-%m-%d %H:%M:%S UTC")
    logger.info("Time prompt: local=%s (%s), utc=%s", local_str, timezone, utc_str)
    return f"Current local date and time: {local_str} ({timezone})"

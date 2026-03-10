"""System prompt builder for the PydanticAI agent."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from business_assistant.config.constants import SYSTEM_PROMPT_BASE
from business_assistant.memory.store import MemoryStore
from business_assistant.plugins.registry import PluginRegistry


def build_system_prompt(registry: PluginRegistry, memory: MemoryStore) -> str:
    """Build the full system prompt from base template, memory, and plugin extras."""
    return SYSTEM_PROMPT_BASE.format(
        memory_contents=memory.format_contents(),
        plugin_extras=registry.system_prompt_extras(),
    )


def build_time_prompt(timezone: str) -> str:
    """Return a line with the current local date, time, and timezone.

    Called dynamically on each agent run so the value is always fresh.
    """
    tz = ZoneInfo(timezone)
    now = datetime.now(tz=tz)
    return f"Current local date and time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')} ({timezone})"

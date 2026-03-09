"""System prompt builder for the PydanticAI agent."""

from __future__ import annotations

from business_assistant.config.constants import SYSTEM_PROMPT_BASE
from business_assistant.memory.store import MemoryStore
from business_assistant.plugins.registry import PluginRegistry


def build_system_prompt(registry: PluginRegistry, memory: MemoryStore) -> str:
    """Build the full system prompt from base template, memory, and plugin extras."""
    return SYSTEM_PROMPT_BASE.format(
        memory_contents=memory.format_contents(),
        plugin_extras=registry.system_prompt_extras(),
    )

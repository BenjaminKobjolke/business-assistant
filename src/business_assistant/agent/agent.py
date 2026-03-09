"""PydanticAI agent setup with memory tools and plugin tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import Agent, RunContext, Tool

from business_assistant.memory.store import MemoryStore
from business_assistant.plugins.registry import PluginRegistry

from .deps import Deps
from .system_prompt import build_system_prompt


def _memory_get(ctx: RunContext[Deps], key: str) -> str:
    """Look up a value from memory by key."""
    value = ctx.deps.memory.get(key)
    if value is None:
        return f"No memory found for key '{key}'."
    return f"{key}: {value}"


def _memory_set(ctx: RunContext[Deps], key: str, value: str) -> str:
    """Store a key-value pair in memory for future reference."""
    ctx.deps.memory.set(key, value)
    return f"Remembered: {key} = {value}"


def _memory_delete(ctx: RunContext[Deps], key: str) -> str:
    """Delete a key from memory."""
    if ctx.deps.memory.delete(key):
        return f"Forgot: {key}"
    return f"No memory found for key '{key}'."


def _memory_list(ctx: RunContext[Deps]) -> str:
    """List all stored memories."""
    data = ctx.deps.memory.list_all()
    if not data:
        return "Memory is empty."
    lines = [f"- {k}: {v}" for k, v in sorted(data.items())]
    return "Stored memories:\n" + "\n".join(lines)


def create_agent(
    registry: PluginRegistry,
    memory: MemoryStore,
    model: Any,
) -> Agent[Deps, str]:
    """Create and configure the PydanticAI agent with all tools.

    Args:
        registry: Plugin registry containing plugin tools.
        memory: Memory store for the memory tools.
        model: The model name (e.g. 'openai:gpt-4o').

    Returns:
        Configured PydanticAI Agent.
    """
    memory_tools = [
        Tool(_memory_get, name="memory_get", description="Look up a value from memory by key."),
        Tool(_memory_set, name="memory_set", description="Store a key-value pair in memory."),
        Tool(
            _memory_delete, name="memory_delete", description="Delete a key from memory."
        ),
        Tool(_memory_list, name="memory_list", description="List all stored memories."),
    ]

    all_tools = memory_tools + registry.all_tools()
    system_prompt = build_system_prompt(registry, memory)

    return Agent(
        model,
        system_prompt=system_prompt,
        tools=all_tools,
        output_type=str,
        deps_type=Deps,
    )

"""PydanticAI agent setup with memory tools and plugin tools."""

from __future__ import annotations

import logging
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic_ai import Agent, RunContext, Tool

from business_assistant.config.constants import DEFAULT_FEEDBACK_DIR, ENV_FEEDBACK_DIR
from business_assistant.memory.store import MemoryStore
from business_assistant.plugins.registry import PluginRegistry

from .deps import Deps
from .system_prompt import build_system_prompt

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


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


def _resolve_feedback_dir() -> Path:
    """Resolve the feedback directory against the project root."""
    raw = os.environ.get(ENV_FEEDBACK_DIR, DEFAULT_FEEDBACK_DIR)
    p = Path(raw)
    if p.is_absolute():
        return p
    return _PROJECT_ROOT / p


_SAFE_FILENAME_RE = re.compile(r"[^\w\-]")


def _write_feedback(ctx: RunContext[Deps], title: str, content: str) -> str:
    """Write a diagnostic feedback report about a tool problem for the developer."""
    feedback_dir = _resolve_feedback_dir()
    feedback_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(tz=UTC).strftime("%Y-%m-%d_%H-%M-%S")
    safe_title = _SAFE_FILENAME_RE.sub("_", title)[:60]
    filename = f"{ts}_{safe_title}.md"

    report = f"# Feedback: {title}\n\n"
    report += f"**Timestamp:** {ts}\n"
    report += f"**User:** {ctx.deps.user_id}\n\n"
    report += f"## Details\n\n{content}\n"

    filepath = feedback_dir / filename
    filepath.write_text(report, encoding="utf-8")
    logger.info("Feedback written to %s", filepath)
    return f"Feedback saved: {filename}"


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

    feedback_tools = [
        Tool(
            _write_feedback,
            name="write_feedback",
            description="Write a diagnostic feedback report about a tool problem.",
        ),
    ]

    all_tools = memory_tools + feedback_tools + registry.all_tools()
    system_prompt = build_system_prompt(registry, memory)

    return Agent(
        model,
        system_prompt=system_prompt,
        tools=all_tools,
        output_type=str,
        deps_type=Deps,
    )

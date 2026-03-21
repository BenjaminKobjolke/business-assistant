"""PydanticAI agent setup with memory tools and plugin tools."""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from pydantic_ai import Agent, RunContext, Tool

from business_assistant.config.constants import (
    DEFAULT_FEEDBACK_DIR,
    DEFAULT_PENDING_RETRIES_SUBDIR,
    ENV_FEEDBACK_DIR,
    LOG_FEEDBACK_WRITTEN,
    LOG_RETRY_COMPLETED,
    LOG_RETRY_SAVED,
    RESP_FEEDBACK_SAVED,
    RESP_MEMORY_DELETED,
    RESP_MEMORY_EMPTY,
    RESP_MEMORY_GET,
    RESP_MEMORY_LIST_HEADER,
    RESP_MEMORY_NOT_FOUND,
    RESP_MEMORY_SET,
    RESP_NO_PENDING_RETRIES,
    RESP_NO_SYNONYMS,
    RESP_PENDING_RETRIES_HEADER,
    RESP_RETRY_ALREADY_COMPLETED,
    RESP_RETRY_COMPLETED,
    RESP_RETRY_CREATED,
    RESP_RETRY_NOT_FOUND,
    RESP_RETRY_READ_ERROR,
    RESP_SYNONYM_DELETED,
    RESP_SYNONYM_NOT_FOUND,
    RESP_SYNONYM_SAVED,
    RESP_SYNONYMS_HEADER,
    RETRY_STATUS_COMPLETED,
    RETRY_STATUS_PENDING,
    SYNONYM_PREFIX,
)
from business_assistant.memory.store import MemoryStore
from business_assistant.plugins.registry import PluginRegistry

from .deps import Deps
from .system_prompt import build_system_prompt, build_time_prompt

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _memory_get(ctx: RunContext[Deps], key: str) -> str:
    """Look up a value from memory by key."""
    value = ctx.deps.memory.get(key)
    if value is None:
        return RESP_MEMORY_NOT_FOUND.format(key=key)
    return RESP_MEMORY_GET.format(key=key, value=value)


def _memory_set(ctx: RunContext[Deps], key: str, value: str) -> str:
    """Store a key-value pair in memory for future reference."""
    ctx.deps.memory.set(key, value)
    return RESP_MEMORY_SET.format(key=key, value=value)


def _memory_delete(ctx: RunContext[Deps], key: str) -> str:
    """Delete a key from memory."""
    if ctx.deps.memory.delete(key):
        return RESP_MEMORY_DELETED.format(key=key)
    return RESP_MEMORY_NOT_FOUND.format(key=key)


def _memory_list(ctx: RunContext[Deps]) -> str:
    """List all stored memories."""
    data = ctx.deps.memory.list_all()
    if not data:
        return RESP_MEMORY_EMPTY
    lines = [f"- {k}: {v}" for k, v in sorted(data.items())]
    return RESP_MEMORY_LIST_HEADER + "\n" + "\n".join(lines)


def _resolve_feedback_dir() -> Path:
    """Resolve the feedback directory against the project root."""
    raw = os.environ.get(ENV_FEEDBACK_DIR, DEFAULT_FEEDBACK_DIR)
    p = Path(raw)
    if p.is_absolute():
        return p
    return _PROJECT_ROOT / p


_SAFE_FILENAME_RE = re.compile(r"[^\w\-]")


@dataclass
class RetryData:
    """Structured pending retry record."""

    id: str
    created_at: str
    user_id: str
    status: str
    user_request: str
    intended_action: str
    feedback_file: str
    completed_at: str | None = None


def _write_feedback(
    ctx: RunContext[Deps], title: str, content: str, intended_action: str = ""
) -> str:
    """Write a diagnostic feedback report about a tool problem for the developer."""
    feedback_dir = _resolve_feedback_dir()
    feedback_dir.mkdir(parents=True, exist_ok=True)

    tz = ZoneInfo(ctx.deps.settings.timezone)
    ts = datetime.now(tz=tz).strftime("%Y-%m-%d_%H-%M-%S")
    safe_title = _SAFE_FILENAME_RE.sub("_", title)[:60]
    filename = f"{ts}_{safe_title}.md"

    report = f"# Feedback: {title}\n\n"
    report += f"**Timestamp:** {ts}\n"
    report += f"**User:** {ctx.deps.user_id}\n\n"
    report += f"## Details\n\n{content}\n"

    filepath = feedback_dir / filename
    filepath.write_text(report, encoding="utf-8")
    logger.info(LOG_FEEDBACK_WRITTEN, filepath)

    result_msg = RESP_FEEDBACK_SAVED.format(filename=filename)

    if intended_action:
        retry_dir = feedback_dir / DEFAULT_PENDING_RETRIES_SUBDIR
        retry_dir.mkdir(parents=True, exist_ok=True)

        retry_id = f"{ts}_{safe_title}"
        retry_data = RetryData(
            id=retry_id,
            created_at=datetime.now(tz=tz).isoformat(),
            user_id=ctx.deps.user_id,
            status=RETRY_STATUS_PENDING,
            user_request=content,
            intended_action=intended_action,
            feedback_file=filename,
        )
        retry_file = retry_dir / f"{retry_id}.json"
        retry_file.write_text(
            json.dumps(dataclasses.asdict(retry_data), indent=2), encoding="utf-8"
        )
        logger.info(LOG_RETRY_SAVED, retry_file)
        result_msg += RESP_RETRY_CREATED.format(retry_id=retry_id)

    return result_msg


def _list_pending_retries(ctx: RunContext[Deps]) -> str:
    """List all pending retry actions that have not been completed yet."""
    feedback_dir = _resolve_feedback_dir()
    retry_dir = feedback_dir / DEFAULT_PENDING_RETRIES_SUBDIR

    if not retry_dir.is_dir():
        return RESP_NO_PENDING_RETRIES

    pending: list[dict[str, Any]] = []
    for json_file in sorted(retry_dir.glob("*.json")):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if data.get("status") == RETRY_STATUS_PENDING:
            pending.append(data)

    if not pending:
        return RESP_NO_PENDING_RETRIES

    lines = []
    for item in pending:
        lines.append(
            f"- **{item['id']}**: {item.get('user_request', 'N/A')}\n"
            f"  Action needed: {item.get('intended_action', 'N/A')}"
        )
    return RESP_PENDING_RETRIES_HEADER.format(count=len(pending)) + "\n" + "\n".join(lines)


def _complete_retry(ctx: RunContext[Deps], retry_id: str) -> str:
    """Mark a pending retry as completed after successfully executing the action."""
    feedback_dir = _resolve_feedback_dir()
    retry_dir = feedback_dir / DEFAULT_PENDING_RETRIES_SUBDIR
    retry_file = retry_dir / f"{retry_id}.json"

    if not retry_file.is_file():
        return RESP_RETRY_NOT_FOUND.format(retry_id=retry_id)

    try:
        data = json.loads(retry_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return RESP_RETRY_READ_ERROR.format(retry_id=retry_id)

    if data.get("status") == RETRY_STATUS_COMPLETED:
        return RESP_RETRY_ALREADY_COMPLETED.format(retry_id=retry_id)

    data["status"] = RETRY_STATUS_COMPLETED
    tz = ZoneInfo(ctx.deps.settings.timezone)
    data["completed_at"] = datetime.now(tz=tz).isoformat()
    retry_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.info(LOG_RETRY_COMPLETED, retry_id)
    return RESP_RETRY_COMPLETED.format(retry_id=retry_id)


def _add_synonym(ctx: RunContext[Deps], synonym: str, target: str) -> str:
    """Define a command synonym so that a custom word triggers an existing command."""
    key = f"{SYNONYM_PREFIX}{synonym.lower().strip()}"
    target_clean = target.lower().strip()
    ctx.deps.memory.set(key, target_clean)
    return RESP_SYNONYM_SAVED.format(synonym=synonym.strip(), target=target_clean)


def _list_synonyms(ctx: RunContext[Deps]) -> str:
    """List all defined command synonyms."""
    all_data = ctx.deps.memory.list_all()
    synonyms = {
        k[len(SYNONYM_PREFIX):]: v
        for k, v in all_data.items()
        if k.startswith(SYNONYM_PREFIX)
    }
    if not synonyms:
        return RESP_NO_SYNONYMS
    lines = [f"- {s} \u2192 {t}" for s, t in sorted(synonyms.items())]
    return RESP_SYNONYMS_HEADER + "\n" + "\n".join(lines)


def _delete_synonym(ctx: RunContext[Deps], synonym: str) -> str:
    """Delete a command synonym."""
    key = f"{SYNONYM_PREFIX}{synonym.lower().strip()}"
    if ctx.deps.memory.delete(key):
        return RESP_SYNONYM_DELETED.format(synonym=synonym.strip())
    return RESP_SYNONYM_NOT_FOUND.format(synonym=synonym.strip())


def get_core_tools() -> list[Tool]:
    """Return the 10 core tools (memory + feedback + synonyms) that are always loaded."""
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
            description=(
                "Write a diagnostic feedback report about a tool problem. "
                "Use the intended_action parameter to save a pending retry "
                "when a user request cannot be fulfilled."
            ),
        ),
        Tool(
            _list_pending_retries,
            name="list_pending_retries",
            description="List all pending retry actions that have not been completed yet.",
        ),
        Tool(
            _complete_retry,
            name="complete_retry",
            description=(
                "Mark a pending retry as completed after successfully "
                "executing the action."
            ),
        ),
    ]

    synonym_tools = [
        Tool(
            _add_synonym,
            name="add_synonym",
            description=(
                "Define a command synonym so that a custom word "
                "triggers an existing command."
            ),
        ),
        Tool(
            _list_synonyms,
            name="list_synonyms",
            description="List all defined command synonyms.",
        ),
        Tool(
            _delete_synonym,
            name="delete_synonym",
            description="Delete a command synonym.",
        ),
    ]

    return memory_tools + feedback_tools + synonym_tools


def create_agent(
    registry: PluginRegistry,
    memory: MemoryStore,
    model: Any,
    timezone: str = "Europe/Berlin",
    core_only: bool = False,
    retries: int = 1,
) -> Agent[Deps, str]:
    """Create and configure the PydanticAI agent.

    Args:
        registry: Plugin registry containing plugin tools.
        memory: Memory store for the memory tools.
        model: The model name (e.g. 'openai:gpt-4o').
        timezone: IANA timezone name for current-time display.
        core_only: If True, create agent with only core tools (memory + feedback).
            Plugin tools are loaded per-request via agent.override().

    Returns:
        Configured PydanticAI Agent.
    """
    core_tools = get_core_tools()

    if core_only:
        all_tools = core_tools
        static_prompt = build_system_prompt(registry, memory, include_plugins=False)
    else:
        all_tools = core_tools + registry.all_tools()
        static_prompt = build_system_prompt(registry, memory)

    agent = Agent(
        model,
        system_prompt=static_prompt,
        tools=all_tools,
        output_type=str,
        deps_type=Deps,
        retries=retries,
    )

    @agent.system_prompt(dynamic=True)
    def _time_prompt() -> str:
        return build_time_prompt(timezone)

    return agent

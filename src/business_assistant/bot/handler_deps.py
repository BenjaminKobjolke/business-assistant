"""Data transfer objects for AIMessageHandler."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic_ai import Agent

from business_assistant.agent.deps import Deps
from business_assistant.agent.router import CategoryRouter
from business_assistant.config.settings import AppSettings
from business_assistant.files.downloader import FileDownloader
from business_assistant.memory.store import MemoryStore
from business_assistant.plugins.registry import PluginRegistry
from business_assistant.usage.tracker import UsageTracker


@dataclass
class HandlerDeps:
    """Bundled dependencies for AIMessageHandler."""

    agent: Agent[Deps, str]
    memory: MemoryStore
    settings: AppSettings
    plugin_data: dict[str, Any] | None = None
    usage_tracker: UsageTracker | None = None
    model_name: str = ""
    provider: str = ""
    router_provider: str = ""
    file_downloader: FileDownloader | None = None
    registry: PluginRegistry | None = None
    router: CategoryRouter | None = None
    core_tools: list[Any] | None = None


@dataclass
class ChatLogEntry:
    """Structured chat log record."""

    user: str
    input_text: str
    output_text: str
    error: bool
    ts_in: datetime | None = None
    ts_out: datetime | None = None
    duration_s: float | None = None
    router_duration_s: float | None = None
    agent_duration_s: float | None = None
    tools_called: list[str] | None = None
    tool_call_count: int | None = None
    llm_requests: int | None = None

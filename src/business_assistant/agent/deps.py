"""Dependencies dataclass passed to PydanticAI tools via RunContext."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from business_assistant.config.settings import AppSettings
from business_assistant.memory.store import MemoryStore


@dataclass
class Deps:
    """Runtime dependencies available to all PydanticAI tools."""

    memory: MemoryStore
    settings: AppSettings
    user_id: str = ""
    plugin_data: dict[str, Any] = field(default_factory=dict)

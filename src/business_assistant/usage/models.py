"""Data transfer objects for usage tracking."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class UsageEntry:
    """Structured usage log record."""

    ts: str
    source: str
    user: str
    model: str
    provider: str
    input_tokens: int | None
    output_tokens: int | None
    cache_read_tokens: int | None
    cache_write_tokens: int | None
    requests: int
    tool_calls_count: int | None
    tools_called: list[str] = field(default_factory=list)
    plugins_involved: list[str] = field(default_factory=list)

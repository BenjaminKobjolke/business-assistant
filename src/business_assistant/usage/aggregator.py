"""Aggregate usage stats and define time periods."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from business_assistant.config.constants import USAGE_SOURCE_BOT

from .prices import ModelPricing, compute_cost


@dataclass(frozen=True)
class ModelStats:
    """Token usage and cost for a single model."""

    model: str
    requests: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cost: float | None


@dataclass(frozen=True)
class SourceStats:
    """Stats for a single source (bot or test) within a period."""

    source: str
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_cache_read_tokens: int
    total_cost: float | None
    by_model: list[ModelStats] = field(default_factory=list)


@dataclass(frozen=True)
class PeriodStats:
    """Aggregated stats for a time period."""

    label: str
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_cache_read_tokens: int
    total_cost: float | None
    by_model: list[ModelStats] = field(default_factory=list)
    by_source: list[SourceStats] = field(default_factory=list)


def get_periods(now: datetime, tz: ZoneInfo) -> list[tuple[str, datetime, datetime]]:
    """Compute 8 standard time periods in the given timezone.

    Returns list of (label, start, end) tuples with timezone-aware datetimes.
    """
    local_now = now.astimezone(tz)
    today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)
    yesterday_start = today_start - timedelta(days=1)

    # Week boundaries (Monday = 0)
    weekday = today_start.weekday()
    this_week_start = today_start - timedelta(days=weekday)
    next_week_start = this_week_start + timedelta(weeks=1)
    last_week_start = this_week_start - timedelta(weeks=1)

    # Month boundaries
    this_month_start = today_start.replace(day=1)
    if this_month_start.month == 12:
        next_month_start = this_month_start.replace(year=this_month_start.year + 1, month=1)
    else:
        next_month_start = this_month_start.replace(month=this_month_start.month + 1)
    last_month_end = this_month_start
    if this_month_start.month == 1:
        last_month_start = this_month_start.replace(year=this_month_start.year - 1, month=12)
    else:
        last_month_start = this_month_start.replace(month=this_month_start.month - 1)

    # Year boundaries
    this_year_start = today_start.replace(month=1, day=1)
    next_year_start = this_year_start.replace(year=this_year_start.year + 1)
    last_year_start = this_year_start.replace(year=this_year_start.year - 1)

    return [
        ("Today", today_start, tomorrow_start),
        ("Yesterday", yesterday_start, today_start),
        ("This Week", this_week_start, next_week_start),
        ("Last Week", last_week_start, this_week_start),
        ("This Month", this_month_start, next_month_start),
        ("Last Month", last_month_start, last_month_end),
        ("This Year", this_year_start, next_year_start),
        ("Last Year", last_year_start, this_year_start),
    ]


def _aggregate_entries(
    entries: list[dict],
    prices: dict[str, ModelPricing],
) -> tuple[list[ModelStats], int, int, int, int, float | None]:
    """Aggregate entries into per-model stats and totals.

    Returns (by_model, total_requests, total_input, total_output, total_cache, total_cost).
    """
    model_data: dict[str, dict] = {}

    for entry in entries:
        model = entry.get("model", "unknown")
        if model not in model_data:
            model_data[model] = {
                "requests": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_read_tokens": 0,
            }
        d = model_data[model]
        d["requests"] += entry.get("requests", 0) or 0
        d["input_tokens"] += entry.get("input_tokens", 0) or 0
        d["output_tokens"] += entry.get("output_tokens", 0) or 0
        d["cache_read_tokens"] += entry.get("cache_read_tokens", 0) or 0

    by_model: list[ModelStats] = []
    total_cost: float | None = 0.0

    for model, d in sorted(model_data.items()):
        cost = compute_cost(
            model, d["input_tokens"], d["output_tokens"], d["cache_read_tokens"], prices
        )
        if cost is None:
            total_cost = None
        elif total_cost is not None:
            total_cost += cost
        by_model.append(ModelStats(
            model=model,
            requests=d["requests"],
            input_tokens=d["input_tokens"],
            output_tokens=d["output_tokens"],
            cache_read_tokens=d["cache_read_tokens"],
            cost=cost,
        ))

    total_requests = sum(d["requests"] for d in model_data.values())
    total_input = sum(d["input_tokens"] for d in model_data.values())
    total_output = sum(d["output_tokens"] for d in model_data.values())
    total_cache = sum(d["cache_read_tokens"] for d in model_data.values())

    return by_model, total_requests, total_input, total_output, total_cache, total_cost


def aggregate(
    entries: list[dict],
    label: str,
    prices: dict[str, ModelPricing],
) -> PeriodStats:
    """Aggregate token usage and costs from filtered entries."""
    by_model, total_req, total_in, total_out, total_cache, total_cost = _aggregate_entries(
        entries, prices,
    )

    # Group by source
    by_source_entries: dict[str, list[dict]] = {}
    for entry in entries:
        src = entry.get("source", USAGE_SOURCE_BOT)
        by_source_entries.setdefault(src, []).append(entry)

    by_source: list[SourceStats] = []
    for src, src_entries in sorted(by_source_entries.items()):
        s_model, s_req, s_in, s_out, s_cache, s_cost = _aggregate_entries(
            src_entries, prices,
        )
        by_source.append(SourceStats(
            source=src,
            total_requests=s_req,
            total_input_tokens=s_in,
            total_output_tokens=s_out,
            total_cache_read_tokens=s_cache,
            total_cost=s_cost,
            by_model=s_model,
        ))

    return PeriodStats(
        label=label,
        total_requests=total_req,
        total_input_tokens=total_in,
        total_output_tokens=total_out,
        total_cache_read_tokens=total_cache,
        total_cost=total_cost,
        by_model=by_model,
        by_source=by_source,
    )

"""Format usage report data as text."""

from __future__ import annotations

from .aggregator import PeriodStats


def format_tokens(n: int) -> str:
    """Format token count with k/M suffixes."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def format_cost(cost: float | None) -> str:
    """Format cost as dollar string or N/A."""
    if cost is None:
        return "N/A"
    return f"${cost:.4f}"


def format_period(stats: PeriodStats) -> str:
    """Format stats for one period as text."""
    if stats.total_requests == 0:
        return f"{stats.label}: (no data)"

    lines = [
        f"{stats.label}: {stats.total_requests} req, {format_cost(stats.total_cost)}",
        f"  in {format_tokens(stats.total_input_tokens)}"
        f" | out {format_tokens(stats.total_output_tokens)}"
        f" | cache {format_tokens(stats.total_cache_read_tokens)}",
    ]
    if len(stats.by_model) > 1:
        for m in stats.by_model:
            lines.append(f"  - {m.model}: {m.requests} req, {format_cost(m.cost)}")
    return "\n".join(lines)


def format_report(period_stats: list[PeriodStats], timezone: str) -> str:
    """Format a complete usage report as a string."""
    lines = [f"Usage Report ({timezone})"]
    for stats in period_stats:
        lines.append("")
        lines.append(format_period(stats))
    return "\n".join(lines)

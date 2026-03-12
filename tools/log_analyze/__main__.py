"""CLI entry point for usage log analysis."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .aggregator import PeriodStats, aggregate, get_periods
from .prices import load_prices
from .reader import filter_entries, read_entries

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_LOG_DIR = str(_PROJECT_ROOT / "logs" / "app" / "usage")
_DEFAULT_LEGACY = str(_PROJECT_ROOT / "data" / "usage.log")


def _format_tokens(n: int) -> str:
    """Format token count with thousand separators."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def _format_cost(cost: float | None) -> str:
    if cost is None:
        return "N/A"
    return f"${cost:.4f}"


def _print_period(stats: PeriodStats) -> None:
    """Print formatted stats for one period."""
    if stats.total_requests == 0:
        print(f"  {stats.label}: (no data)")
        return

    print(f"  {stats.label}:")
    print(
        f"    Total: {stats.total_requests} requests, "
        f"in={_format_tokens(stats.total_input_tokens)}, "
        f"out={_format_tokens(stats.total_output_tokens)}, "
        f"cache_read={_format_tokens(stats.total_cache_read_tokens)}, "
        f"cost={_format_cost(stats.total_cost)}"
    )
    if len(stats.by_model) > 1:
        for m in stats.by_model:
            print(
                f"      {m.model}: {m.requests} req, "
                f"in={_format_tokens(m.input_tokens)}, "
                f"out={_format_tokens(m.output_tokens)}, "
                f"cost={_format_cost(m.cost)}"
            )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Analyze usage logs: tokens + costs by period")
    parser.add_argument(
        "--force-update-prices",
        action="store_true",
        help="Force re-fetch pricing from litellm (bypasses 24h cache)",
    )
    parser.add_argument(
        "--log-dir",
        default=_DEFAULT_LOG_DIR,
        help=f"Usage log directory (default: {_DEFAULT_LOG_DIR})",
    )
    parser.add_argument(
        "--legacy-file",
        default=_DEFAULT_LEGACY,
        help=f"Legacy usage.log file (default: {_DEFAULT_LEGACY})",
    )
    parser.add_argument(
        "--no-legacy",
        action="store_true",
        help="Skip legacy usage.log file",
    )
    parser.add_argument(
        "--timezone",
        default=os.environ.get("USER_TIMEZONE", "Europe/Berlin"),
        help="Timezone for period boundaries (default: USER_TIMEZONE env or Europe/Berlin)",
    )
    args = parser.parse_args(argv)

    tz = ZoneInfo(args.timezone)
    legacy = None if args.no_legacy else args.legacy_file

    print("Loading prices...")
    prices = load_prices(force=args.force_update_prices)
    print(f"Loaded {len(prices)} model prices.\n")

    entries = read_entries(args.log_dir, legacy_file=legacy)
    if not entries:
        print("No usage log entries found.")
        sys.exit(0)

    print(f"Found {len(entries)} total log entries.\n")

    now = datetime.now(tz=UTC)
    periods = get_periods(now, tz)

    print(f"Usage Report (timezone: {args.timezone})")
    print("=" * 60)

    for label, start, end in periods:
        filtered = filter_entries(entries, start, end)
        stats = aggregate(filtered, label, prices)
        _print_period(stats)

    print()


if __name__ == "__main__":
    main()

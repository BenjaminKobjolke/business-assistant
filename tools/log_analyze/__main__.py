"""CLI entry point for usage log analysis."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from business_assistant.usage.aggregator import aggregate, get_periods
from business_assistant.usage.formatter import format_period
from business_assistant.usage.prices import load_prices
from business_assistant.usage.reader import filter_entries, read_entries

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_LOG_DIR = str(_PROJECT_ROOT / "logs" / "app" / "usage")
_DEFAULT_LEGACY = str(_PROJECT_ROOT / "data" / "usage.log")


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
        print(format_period(stats))

    print()


if __name__ == "__main__":
    main()

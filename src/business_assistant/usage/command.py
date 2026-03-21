"""Usage report command handler for the chatbot."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from bot_commander.types import BotResponse

from business_assistant.config.constants import (
    CMD_USAGE,
    DEFAULT_LEGACY_USAGE_FILE,
    RESP_NO_USAGE_DATA,
    RESP_USAGE_REPORT_FAILED,
)
from business_assistant.config.settings import AppSettings

from .aggregator import aggregate, get_periods
from .formatter import format_report
from .prices import load_prices
from .reader import filter_entries, read_entries

logger = logging.getLogger(__name__)


def create_usage_handler(settings: AppSettings) -> Callable:
    """Return a command handler that generates a usage report."""

    def usage_handler(text: str, user_id: str, plugin_data: dict) -> BotResponse | None:
        if text.lower().strip() not in CMD_USAGE:
            return None

        try:
            tz = ZoneInfo(settings.timezone)
            prices = load_prices()
            entries = read_entries(
                settings.usage_log_dir,
                legacy_file=DEFAULT_LEGACY_USAGE_FILE,
            )

            if not entries:
                return BotResponse(text=RESP_NO_USAGE_DATA)

            now = datetime.now(tz=UTC)
            periods = get_periods(now, tz)

            period_stats = [
                aggregate(filter_entries(entries, start, end), label, prices)
                for label, start, end in periods
            ]

            report = format_report(period_stats, settings.timezone)
            return BotResponse(text=report)
        except Exception:
            logger.error("Usage report generation failed", exc_info=True)
            return BotResponse(text=RESP_USAGE_REPORT_FAILED)

    return usage_handler

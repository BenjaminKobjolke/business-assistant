"""Tests for usage report formatting."""

from __future__ import annotations

from business_assistant.usage.aggregator import ModelStats, PeriodStats, SourceStats
from business_assistant.usage.formatter import (
    format_cost,
    format_period,
    format_report,
    format_tokens,
)


class TestFormatTokens:
    def test_small(self) -> None:
        assert format_tokens(500) == "500"

    def test_thousands(self) -> None:
        assert format_tokens(1500) == "1.5k"

    def test_millions(self) -> None:
        assert format_tokens(1_500_000) == "1.5M"

    def test_zero(self) -> None:
        assert format_tokens(0) == "0"

    def test_exact_thousand(self) -> None:
        assert format_tokens(1000) == "1.0k"


class TestFormatCost:
    def test_none(self) -> None:
        assert format_cost(None) == "N/A"

    def test_value(self) -> None:
        assert format_cost(0.1234) == "$0.1234"

    def test_zero(self) -> None:
        assert format_cost(0.0) == "$0.0000"


class TestFormatPeriod:
    def test_no_data(self) -> None:
        stats = PeriodStats(
            label="Today",
            total_requests=0,
            total_input_tokens=0,
            total_output_tokens=0,
            total_cache_read_tokens=0,
            total_cost=None,
        )
        result = format_period(stats)
        assert result == "Today: (no data)"

    def test_with_data(self) -> None:
        stats = PeriodStats(
            label="Today",
            total_requests=5,
            total_input_tokens=1000,
            total_output_tokens=500,
            total_cache_read_tokens=100,
            total_cost=0.05,
            by_model=[
                ModelStats(
                    model="gpt-4o",
                    requests=5,
                    input_tokens=1000,
                    output_tokens=500,
                    cache_read_tokens=100,
                    cost=0.05,
                ),
            ],
        )
        result = format_period(stats)
        assert "Today: 5 req, $0.0500" in result
        assert "in 1.0k | out 500 | cache 100" in result

    def test_multiple_models_shows_breakdown(self) -> None:
        stats = PeriodStats(
            label="Today",
            total_requests=3,
            total_input_tokens=300,
            total_output_tokens=150,
            total_cache_read_tokens=0,
            total_cost=0.01,
            by_model=[
                ModelStats("gpt-4o", 2, 200, 100, 0, 0.008),
                ModelStats("gpt-4o-mini", 1, 100, 50, 0, 0.002),
            ],
        )
        result = format_period(stats)
        assert "- gpt-4o: 2 req, $0.0080" in result
        assert "- gpt-4o-mini: 1 req, $0.0020" in result


    def test_source_breakdown_shown_when_multiple(self) -> None:
        stats = PeriodStats(
            label="Today",
            total_requests=7,
            total_input_tokens=700,
            total_output_tokens=350,
            total_cache_read_tokens=0,
            total_cost=0.08,
            by_model=[ModelStats("gpt-4o", 7, 700, 350, 0, 0.08)],
            by_source=[
                SourceStats("bot", 5, 500, 250, 0, 0.06),
                SourceStats("test", 2, 200, 100, 0, 0.02),
            ],
        )
        result = format_period(stats)
        assert "[bot] 5 req, $0.0600" in result
        assert "[test] 2 req, $0.0200" in result

    def test_source_breakdown_hidden_when_single(self) -> None:
        stats = PeriodStats(
            label="Today",
            total_requests=5,
            total_input_tokens=500,
            total_output_tokens=250,
            total_cache_read_tokens=0,
            total_cost=0.05,
            by_model=[ModelStats("gpt-4o", 5, 500, 250, 0, 0.05)],
            by_source=[
                SourceStats("bot", 5, 500, 250, 0, 0.05),
            ],
        )
        result = format_period(stats)
        assert "[bot]" not in result


class TestFormatReport:
    def test_structure(self) -> None:
        period_stats = [
            PeriodStats("Today", 0, 0, 0, 0, None),
            PeriodStats("Yesterday", 1, 100, 50, 0, 0.01),
        ]
        report = format_report(period_stats, "Europe/Berlin")
        assert "Usage Report (Europe/Berlin)" in report
        assert "Today: (no data)" in report
        assert "Yesterday: 1 req, $0.0100" in report
        assert "\n\n" in report  # blank lines between periods

"""Tests for the log_analyze CLI tool."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from log_analyze.aggregator import aggregate, get_periods
from log_analyze.prices import ModelPricing, compute_cost
from log_analyze.reader import filter_entries, read_entries


class TestComputeCost:
    def test_known_model(self) -> None:
        prices = {
            "gpt-4o": ModelPricing(
                input_cost=0.000005,
                output_cost=0.000015,
                cache_read_cost=0.0000025,
            ),
        }
        cost = compute_cost("gpt-4o", 1000, 500, 200, prices)
        assert cost is not None
        expected = 1000 * 0.000005 + 500 * 0.000015 + 200 * 0.0000025
        assert abs(cost - expected) < 1e-10

    def test_unknown_model(self) -> None:
        prices = {
            "gpt-4o": ModelPricing(input_cost=0.01, output_cost=0.03, cache_read_cost=0.005),
        }
        cost = compute_cost("unknown-model", 100, 50, 0, prices)
        assert cost is None


class TestReadEntries:
    def test_from_jsonl_files(self, tmp_path) -> None:
        log_dir = tmp_path / "usage"
        log_dir.mkdir()

        entry1 = {"ts": "2026-03-10T10:00:00+00:00", "model": "gpt-4o", "input_tokens": 100}
        entry2 = {"ts": "2026-03-11T10:00:00+00:00", "model": "gpt-4o", "input_tokens": 200}

        (log_dir / "usage.2026-03-10.jsonl").write_text(
            json.dumps(entry1) + "\n", encoding="utf-8"
        )
        (log_dir / "usage.2026-03-11.jsonl").write_text(
            json.dumps(entry2) + "\n", encoding="utf-8"
        )

        entries = read_entries(log_dir)
        assert len(entries) == 2
        assert entries[0]["input_tokens"] == 100
        assert entries[1]["input_tokens"] == 200

    def test_with_legacy(self, tmp_path) -> None:
        log_dir = tmp_path / "usage"
        log_dir.mkdir()

        new_entry = {"ts": "2026-03-11T10:00:00+00:00", "model": "gpt-4o", "input_tokens": 200}
        (log_dir / "usage.2026-03-11.jsonl").write_text(
            json.dumps(new_entry) + "\n", encoding="utf-8"
        )

        legacy = tmp_path / "usage.log"
        old_entry = {"ts": "2026-01-01T10:00:00+00:00", "model": "gpt-4o", "input_tokens": 50}
        legacy.write_text(json.dumps(old_entry) + "\n", encoding="utf-8")

        entries = read_entries(log_dir, legacy_file=legacy)
        assert len(entries) == 2

    def test_skips_malformed_lines(self, tmp_path) -> None:
        log_dir = tmp_path / "usage"
        log_dir.mkdir()
        (log_dir / "usage.2026-03-10.jsonl").write_text(
            "not json\n" + json.dumps({"ts": "2026-03-10T10:00:00+00:00"}) + "\n",
            encoding="utf-8",
        )
        entries = read_entries(log_dir)
        assert len(entries) == 1


class TestFilterEntries:
    def test_by_date_range(self) -> None:
        entries = [
            {"ts": "2026-03-10T10:00:00+00:00"},
            {"ts": "2026-03-11T10:00:00+00:00"},
            {"ts": "2026-03-12T10:00:00+00:00"},
        ]
        start = datetime(2026, 3, 11, tzinfo=UTC)
        end = datetime(2026, 3, 12, tzinfo=UTC)

        filtered = filter_entries(entries, start, end)
        assert len(filtered) == 1
        assert filtered[0]["ts"] == "2026-03-11T10:00:00+00:00"

    def test_empty_on_no_match(self) -> None:
        entries = [{"ts": "2026-03-10T10:00:00+00:00"}]
        start = datetime(2026, 3, 15, tzinfo=UTC)
        end = datetime(2026, 3, 16, tzinfo=UTC)
        assert filter_entries(entries, start, end) == []


class TestAggregate:
    def test_sums_tokens_and_costs(self) -> None:
        entries = [
            {
                "model": "gpt-4o",
                "requests": 2,
                "input_tokens": 100,
                "output_tokens": 50,
                "cache_read_tokens": 10,
            },
            {
                "model": "gpt-4o",
                "requests": 1,
                "input_tokens": 200,
                "output_tokens": 100,
                "cache_read_tokens": 20,
            },
        ]
        prices = {
            "gpt-4o": ModelPricing(
                input_cost=0.000005,
                output_cost=0.000015,
                cache_read_cost=0.0000025,
            ),
        }

        stats = aggregate(entries, "Today", prices)

        assert stats.label == "Today"
        assert stats.total_requests == 3
        assert stats.total_input_tokens == 300
        assert stats.total_output_tokens == 150
        assert stats.total_cache_read_tokens == 30
        assert stats.total_cost is not None
        expected = 300 * 0.000005 + 150 * 0.000015 + 30 * 0.0000025
        assert abs(stats.total_cost - expected) < 1e-10
        assert len(stats.by_model) == 1
        assert stats.by_model[0].model == "gpt-4o"

    def test_multiple_models(self) -> None:
        entries = [
            {"model": "gpt-4o", "requests": 1, "input_tokens": 100, "output_tokens": 50,
             "cache_read_tokens": 0},
            {"model": "gpt-4o-mini", "requests": 1, "input_tokens": 200, "output_tokens": 100,
             "cache_read_tokens": 0},
        ]
        prices = {
            "gpt-4o": ModelPricing(input_cost=0.000005, output_cost=0.000015, cache_read_cost=0.0),
            "gpt-4o-mini": ModelPricing(
                input_cost=0.00000015, output_cost=0.0000006, cache_read_cost=0.0
            ),
        }
        stats = aggregate(entries, "Today", prices)
        assert len(stats.by_model) == 2


class TestGetPeriods:
    def test_returns_all_labels(self) -> None:
        tz = ZoneInfo("Europe/Berlin")
        now = datetime(2026, 3, 12, 14, 0, 0, tzinfo=UTC)
        periods = get_periods(now, tz)

        labels = [p[0] for p in periods]
        assert labels == [
            "Today", "Yesterday", "This Week", "Last Week",
            "This Month", "Last Month", "This Year", "Last Year",
        ]
        assert len(periods) == 8

    def test_today_boundaries(self) -> None:
        tz = ZoneInfo("Europe/Berlin")
        now = datetime(2026, 3, 12, 14, 0, 0, tzinfo=UTC)
        periods = get_periods(now, tz)

        today_label, today_start, today_end = periods[0]
        assert today_label == "Today"
        assert today_start.day == 12
        assert today_end.day == 13
        assert today_end - today_start == timedelta(days=1)

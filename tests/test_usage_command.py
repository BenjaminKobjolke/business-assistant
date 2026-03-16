"""Tests for the usage command handler."""

from __future__ import annotations

import json
from unittest.mock import patch

from business_assistant.usage.command import create_usage_handler
from tests.conftest import make_test_settings


class TestUsageCommand:
    def test_returns_report(self, tmp_path) -> None:
        log_dir = tmp_path / "usage"
        log_dir.mkdir()
        entry = {
            "ts": "2026-03-15T10:00:00+00:00",
            "model": "gpt-4o",
            "requests": 1,
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_read_tokens": 0,
        }
        (log_dir / "usage.2026-03-15.jsonl").write_text(
            json.dumps(entry) + "\n", encoding="utf-8"
        )
        settings = make_test_settings(usage_log_dir=str(log_dir))
        handler = create_usage_handler(settings)

        with (
            patch("business_assistant.usage.command.load_prices", return_value={}),
            patch(
                "business_assistant.usage.command.DEFAULT_LEGACY_USAGE_FILE",
                str(tmp_path / "nonexistent.log"),
            ),
        ):
            result = handler("usage", "user@test.com", {})

        assert result is not None
        assert "Usage Report" in result.text

    def test_ignores_non_usage(self) -> None:
        settings = make_test_settings()
        handler = create_usage_handler(settings)
        assert handler("hello", "user@test.com", {}) is None

    def test_empty_logs(self, tmp_path) -> None:
        log_dir = tmp_path / "usage"
        log_dir.mkdir()
        settings = make_test_settings(usage_log_dir=str(log_dir))
        handler = create_usage_handler(settings)

        with (
            patch("business_assistant.usage.command.load_prices", return_value={}),
            patch(
                "business_assistant.usage.command.DEFAULT_LEGACY_USAGE_FILE",
                str(tmp_path / "nonexistent.log"),
            ),
        ):
            result = handler("usage", "user@test.com", {})

        assert result is not None
        assert "No usage data found" in result.text

    def test_error_handling(self) -> None:
        settings = make_test_settings()
        handler = create_usage_handler(settings)

        with patch(
            "business_assistant.usage.command.load_prices",
            side_effect=RuntimeError("boom"),
        ):
            result = handler("usage", "user@test.com", {})

        assert result is not None
        assert "Failed to generate" in result.text

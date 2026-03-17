"""Tests for UsageTracker."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import patch

from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.usage import RunUsage

from business_assistant.usage.tracker import UsageTracker


class TestExtractToolNames:
    def test_extracts_tool_names_from_responses(self) -> None:
        messages = [
            ModelResponse(parts=[
                ToolCallPart(tool_name="search_emails", args={}, tool_call_id="1"),
            ]),
            ModelResponse(parts=[
                ToolCallPart(tool_name="show_email", args={}, tool_call_id="2"),
                TextPart(content="Here are the results"),
            ]),
        ]
        result = UsageTracker._extract_tool_names(messages)
        assert result == ["search_emails", "show_email"]

    def test_deduplicates_tool_names(self) -> None:
        messages = [
            ModelResponse(parts=[
                ToolCallPart(tool_name="search_emails", args={}, tool_call_id="1"),
            ]),
            ModelResponse(parts=[
                ToolCallPart(tool_name="search_emails", args={}, tool_call_id="2"),
            ]),
        ]
        result = UsageTracker._extract_tool_names(messages)
        assert result == ["search_emails"]

    def test_empty_messages(self) -> None:
        assert UsageTracker._extract_tool_names([]) == []

    def test_no_tool_calls(self) -> None:
        messages = [
            ModelResponse(parts=[TextPart(content="hello")]),
        ]
        assert UsageTracker._extract_tool_names(messages) == []

    def test_ignores_non_model_response(self) -> None:
        messages = [{"role": "user", "content": "hi"}]
        assert UsageTracker._extract_tool_names(messages) == []


class TestUsageTrackerLog:
    def test_writes_jsonl_entry(self, tmp_path) -> None:
        log_dir = str(tmp_path / "usage")
        tracker = UsageTracker(log_dir, {"search_emails": "imap"})

        usage = RunUsage(input_tokens=100, output_tokens=50, requests=2, tool_calls=1)
        messages = [
            ModelResponse(parts=[
                ToolCallPart(tool_name="search_emails", args={}, tool_call_id="1"),
            ]),
        ]
        tracker.log(usage, messages, "user@test.com", "gpt-4o")

        files = list((tmp_path / "usage").glob("usage.*.jsonl"))
        assert len(files) == 1

        with open(files[0], encoding="utf-8") as f:
            entry = json.loads(f.readline())

        assert entry["user"] == "user@test.com"
        assert entry["model"] == "gpt-4o"
        assert entry["source"] == "bot"
        assert entry["input_tokens"] == 100
        assert entry["output_tokens"] == 50
        assert entry["requests"] == 2
        assert entry["tool_calls_count"] == 1
        assert entry["tools_called"] == ["search_emails"]
        assert entry["plugins_involved"] == ["imap"]
        assert "ts" in entry

    def test_daily_file_naming(self, tmp_path) -> None:
        log_dir = str(tmp_path / "usage")
        tracker = UsageTracker(log_dir, {})

        fixed_time = datetime(2026, 3, 12, 14, 30, 0, tzinfo=UTC)
        with patch("business_assistant.usage.tracker.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_time
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            tracker.log(RunUsage(input_tokens=10), [], "a@test", "gpt-4o")

        expected_file = tmp_path / "usage" / "usage.2026-03-12.jsonl"
        assert expected_file.exists()

    def test_resolves_plugins_from_map(self, tmp_path) -> None:
        log_dir = str(tmp_path / "usage")
        tool_map = {"search_emails": "imap", "list_events": "calendar"}
        tracker = UsageTracker(log_dir, tool_map)

        messages = [
            ModelResponse(parts=[
                ToolCallPart(tool_name="search_emails", args={}, tool_call_id="1"),
                ToolCallPart(tool_name="list_events", args={}, tool_call_id="2"),
            ]),
        ]
        tracker.log(RunUsage(), messages, "user@test.com", "gpt-4o")

        files = list((tmp_path / "usage").glob("usage.*.jsonl"))
        with open(files[0], encoding="utf-8") as f:
            entry = json.loads(f.readline())

        assert set(entry["plugins_involved"]) == {"imap", "calendar"}

    def test_unknown_tool_maps_to_core(self, tmp_path) -> None:
        log_dir = str(tmp_path / "usage")
        tracker = UsageTracker(log_dir, {})

        messages = [
            ModelResponse(parts=[
                ToolCallPart(tool_name="memory_get", args={}, tool_call_id="1"),
            ]),
        ]
        tracker.log(RunUsage(), messages, "user@test.com", "gpt-4o")

        files = list((tmp_path / "usage").glob("usage.*.jsonl"))
        with open(files[0], encoding="utf-8") as f:
            entry = json.loads(f.readline())

        assert entry["plugins_involved"] == ["core"]

    def test_no_tool_calls_empty_lists(self, tmp_path) -> None:
        log_dir = str(tmp_path / "usage")
        tracker = UsageTracker(log_dir, {})

        messages = [ModelResponse(parts=[TextPart(content="hello")])]
        tracker.log(RunUsage(), messages, "user@test.com", "gpt-4o")

        files = list((tmp_path / "usage").glob("usage.*.jsonl"))
        with open(files[0], encoding="utf-8") as f:
            entry = json.loads(f.readline())

        assert entry["tools_called"] == []
        assert entry["plugins_involved"] == []

    def test_multiple_entries_appended(self, tmp_path) -> None:
        log_dir = str(tmp_path / "usage")
        tracker = UsageTracker(log_dir, {})

        tracker.log(RunUsage(input_tokens=10), [], "a@test", "gpt-4o")
        tracker.log(RunUsage(input_tokens=20), [], "b@test", "gpt-4o")

        files = list((tmp_path / "usage").glob("usage.*.jsonl"))
        assert len(files) == 1

        with open(files[0], encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) == 2
        assert json.loads(lines[0])["input_tokens"] == 10
        assert json.loads(lines[1])["input_tokens"] == 20

    def test_silent_on_write_failure(self, tmp_path) -> None:
        log_dir = str(tmp_path / "usage")
        tracker = UsageTracker(log_dir, {})
        # Point to a non-existent deep path that can't be created
        tracker._log_dir = tmp_path / "no" / "such" / "dir"
        # Should not raise
        tracker.log(RunUsage(), [], "user@test.com", "gpt-4o")

    def test_explicit_source_test(self, tmp_path) -> None:
        log_dir = str(tmp_path / "usage")
        tracker = UsageTracker(log_dir, {})

        tracker.log(RunUsage(input_tokens=10), [], "user@test.com", "gpt-4o", source="test")

        files = list((tmp_path / "usage").glob("usage.*.jsonl"))
        with open(files[0], encoding="utf-8") as f:
            entry = json.loads(f.readline())

        assert entry["source"] == "test"

    def test_creates_directory_on_init(self, tmp_path) -> None:
        log_dir = str(tmp_path / "new" / "usage")
        UsageTracker(log_dir, {})
        assert (tmp_path / "new" / "usage").is_dir()

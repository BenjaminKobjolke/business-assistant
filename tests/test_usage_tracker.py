"""Tests for UsageTracker."""

from __future__ import annotations

import json

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
        log_file = str(tmp_path / "usage.log")
        tracker = UsageTracker(log_file, {"search_emails": "imap"})

        usage = RunUsage(input_tokens=100, output_tokens=50, requests=2, tool_calls=1)
        messages = [
            ModelResponse(parts=[
                ToolCallPart(tool_name="search_emails", args={}, tool_call_id="1"),
            ]),
        ]
        tracker.log(usage, messages, "user@test.com", "gpt-4o")

        with open(log_file, encoding="utf-8") as f:
            entry = json.loads(f.readline())

        assert entry["user"] == "user@test.com"
        assert entry["model"] == "gpt-4o"
        assert entry["input_tokens"] == 100
        assert entry["output_tokens"] == 50
        assert entry["requests"] == 2
        assert entry["tool_calls_count"] == 1
        assert entry["tools_called"] == ["search_emails"]
        assert entry["plugins_involved"] == ["imap"]
        assert "ts" in entry

    def test_resolves_plugins_from_map(self, tmp_path) -> None:
        log_file = str(tmp_path / "usage.log")
        tool_map = {"search_emails": "imap", "list_events": "calendar"}
        tracker = UsageTracker(log_file, tool_map)

        messages = [
            ModelResponse(parts=[
                ToolCallPart(tool_name="search_emails", args={}, tool_call_id="1"),
                ToolCallPart(tool_name="list_events", args={}, tool_call_id="2"),
            ]),
        ]
        tracker.log(RunUsage(), messages, "user@test.com", "gpt-4o")

        with open(log_file, encoding="utf-8") as f:
            entry = json.loads(f.readline())

        assert set(entry["plugins_involved"]) == {"imap", "calendar"}

    def test_unknown_tool_maps_to_core(self, tmp_path) -> None:
        log_file = str(tmp_path / "usage.log")
        tracker = UsageTracker(log_file, {})

        messages = [
            ModelResponse(parts=[
                ToolCallPart(tool_name="memory_get", args={}, tool_call_id="1"),
            ]),
        ]
        tracker.log(RunUsage(), messages, "user@test.com", "gpt-4o")

        with open(log_file, encoding="utf-8") as f:
            entry = json.loads(f.readline())

        assert entry["plugins_involved"] == ["core"]

    def test_no_tool_calls_empty_lists(self, tmp_path) -> None:
        log_file = str(tmp_path / "usage.log")
        tracker = UsageTracker(log_file, {})

        messages = [ModelResponse(parts=[TextPart(content="hello")])]
        tracker.log(RunUsage(), messages, "user@test.com", "gpt-4o")

        with open(log_file, encoding="utf-8") as f:
            entry = json.loads(f.readline())

        assert entry["tools_called"] == []
        assert entry["plugins_involved"] == []

    def test_multiple_entries_appended(self, tmp_path) -> None:
        log_file = str(tmp_path / "usage.log")
        tracker = UsageTracker(log_file, {})

        tracker.log(RunUsage(input_tokens=10), [], "a@test", "gpt-4o")
        tracker.log(RunUsage(input_tokens=20), [], "b@test", "gpt-4o")

        with open(log_file, encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) == 2
        assert json.loads(lines[0])["input_tokens"] == 10
        assert json.loads(lines[1])["input_tokens"] == 20

    def test_silent_on_write_failure(self, tmp_path) -> None:
        # Point to a non-existent deep path that can't be created
        tracker = UsageTracker("", {})
        tracker._path = tmp_path / "no" / "such" / "dir" / "usage.log"
        # Should not raise
        tracker.log(RunUsage(), [], "user@test.com", "gpt-4o")

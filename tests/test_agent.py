"""Tests for agent creation and tool wiring."""

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from pydantic_ai import RunContext, Tool
from pydantic_ai.models.test import TestModel

from business_assistant.agent.agent import (
    _add_synonym,
    _complete_retry,
    _delete_synonym,
    _list_pending_retries,
    _list_synonyms,
    _write_feedback,
    create_agent,
)
from business_assistant.agent.deps import Deps
from business_assistant.agent.system_prompt import build_time_prompt
from business_assistant.config.constants import DEFAULT_PENDING_RETRIES_SUBDIR, SYNONYM_PREFIX
from business_assistant.memory.store import MemoryStore
from business_assistant.plugins.registry import PluginInfo, PluginRegistry
from tests.conftest import make_test_settings


class TestAgentCreation:
    def test_create_agent_with_memory_tools(self, tmp_memory_file: str) -> None:
        memory = MemoryStore(tmp_memory_file)
        registry = PluginRegistry()

        agent = create_agent(registry, memory, TestModel())

        tool_names = {t.name for t in agent._function_toolset.tools.values()}
        assert "memory_get" in tool_names
        assert "memory_set" in tool_names
        assert "memory_delete" in tool_names
        assert "memory_list" in tool_names

    def test_create_agent_with_plugin_tools(self, tmp_memory_file: str) -> None:
        def dummy_tool(ctx: RunContext[Deps]) -> str:
            return "dummy"

        memory = MemoryStore(tmp_memory_file)
        registry = PluginRegistry()
        registry.register(
            PluginInfo(name="test", description="Test"),
            [Tool(dummy_tool, name="test_tool", description="A test tool")],
        )

        agent = create_agent(registry, memory, TestModel())

        tool_names = {t.name for t in agent._function_toolset.tools.values()}
        assert "test_tool" in tool_names
        assert "memory_get" in tool_names

    def test_create_agent_has_write_feedback_tool(self, tmp_memory_file: str) -> None:
        memory = MemoryStore(tmp_memory_file)
        registry = PluginRegistry()
        agent = create_agent(registry, memory, TestModel())
        tool_names = {t.name for t in agent._function_toolset.tools.values()}
        assert "write_feedback" in tool_names

    def test_create_agent_has_retry_tools(self, tmp_memory_file: str) -> None:
        memory = MemoryStore(tmp_memory_file)
        registry = PluginRegistry()
        agent = create_agent(registry, memory, TestModel())
        tool_names = {t.name for t in agent._function_toolset.tools.values()}
        assert "list_pending_retries" in tool_names
        assert "complete_retry" in tool_names

    def test_create_agent_passes_retries(self, tmp_memory_file: str) -> None:
        memory = MemoryStore(tmp_memory_file)
        registry = PluginRegistry()
        agent = create_agent(registry, memory, TestModel(), retries=5)
        assert agent._max_result_retries == 5


class TestBuildTimePrompt:
    def test_returns_correct_format(self) -> None:
        fixed_utc = datetime(2026, 3, 11, 15, 5, 0, tzinfo=UTC)
        with patch(
            "business_assistant.agent.system_prompt.datetime",
        ) as mock_dt:
            mock_dt.now.return_value = fixed_utc
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = build_time_prompt("Europe/Berlin")

        assert "2026-03-11 16:05:00 CET" in result
        assert "(Europe/Berlin)" in result

    def test_summer_time(self) -> None:
        fixed_utc = datetime(2026, 7, 15, 12, 0, 0, tzinfo=UTC)
        with patch(
            "business_assistant.agent.system_prompt.datetime",
        ) as mock_dt:
            mock_dt.now.return_value = fixed_utc
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = build_time_prompt("Europe/Berlin")

        assert "2026-07-15 14:00:00 CEST" in result


class TestWriteFeedback:
    def test_creates_feedback_file(self, tmp_path, monkeypatch) -> None:
        feedback_dir = tmp_path / "feedback"
        monkeypatch.setenv("FEEDBACK_DIR", str(feedback_dir))

        settings = make_test_settings()
        deps = Deps(
            memory=MemoryStore(str(tmp_path / "mem.json")),
            settings=settings,
            user_id="tester@test.com",
            plugin_data={},
        )
        ctx = MagicMock(spec=RunContext)
        ctx.deps = deps

        result = _write_feedback(ctx, "search broken", "search_emails returned 0 results")
        assert "Feedback saved" in result
        assert feedback_dir.is_dir()

        files = list(feedback_dir.glob("*.md"))
        assert len(files) == 1
        content = files[0].read_text(encoding="utf-8")
        assert "search broken" in content
        assert "search_emails returned 0 results" in content
        assert "tester@test.com" in content

    def test_write_feedback_without_intended_action_no_retry_file(
        self, tmp_path, monkeypatch
    ) -> None:
        feedback_dir = tmp_path / "feedback"
        monkeypatch.setenv("FEEDBACK_DIR", str(feedback_dir))

        settings = make_test_settings()
        deps = Deps(
            memory=MemoryStore(str(tmp_path / "mem.json")),
            settings=settings,
            user_id="tester@test.com",
            plugin_data={},
        )
        ctx = MagicMock(spec=RunContext)
        ctx.deps = deps

        _write_feedback(ctx, "some issue", "details here")
        retry_dir = feedback_dir / DEFAULT_PENDING_RETRIES_SUBDIR
        assert not retry_dir.exists()

    def test_write_feedback_with_intended_action_creates_retry(
        self, tmp_path, monkeypatch
    ) -> None:
        feedback_dir = tmp_path / "feedback"
        monkeypatch.setenv("FEEDBACK_DIR", str(feedback_dir))

        settings = make_test_settings()
        deps = Deps(
            memory=MemoryStore(str(tmp_path / "mem.json")),
            settings=settings,
            user_id="tester@test.com",
            plugin_data={},
        )
        ctx = MagicMock(spec=RunContext)
        ctx.deps = deps

        result = _write_feedback(
            ctx, "missing feature", "User wants X", intended_action="implement tool Y"
        )
        assert "Pending retry created" in result

        retry_dir = feedback_dir / DEFAULT_PENDING_RETRIES_SUBDIR
        assert retry_dir.is_dir()
        retry_files = list(retry_dir.glob("*.json"))
        assert len(retry_files) == 1

        data = json.loads(retry_files[0].read_text(encoding="utf-8"))
        assert data["status"] == "pending"
        assert data["user_request"] == "User wants X"
        assert data["intended_action"] == "implement tool Y"
        assert data["user_id"] == "tester@test.com"
        assert data["completed_at"] is None
        assert data["feedback_file"].endswith(".md")


class TestListPendingRetries:
    def _make_ctx(self, tmp_path):
        settings = make_test_settings()
        deps = Deps(
            memory=MemoryStore(str(tmp_path / "mem.json")),
            settings=settings,
            user_id="tester@test.com",
            plugin_data={},
        )
        ctx = MagicMock(spec=RunContext)
        ctx.deps = deps
        return ctx

    def test_list_retries_empty(self, tmp_path, monkeypatch) -> None:
        feedback_dir = tmp_path / "feedback"
        monkeypatch.setenv("FEEDBACK_DIR", str(feedback_dir))
        ctx = self._make_ctx(tmp_path)
        result = _list_pending_retries(ctx)
        assert result == "No pending retries found."

    def test_list_retries_with_pending(self, tmp_path, monkeypatch) -> None:
        feedback_dir = tmp_path / "feedback"
        monkeypatch.setenv("FEEDBACK_DIR", str(feedback_dir))
        retry_dir = feedback_dir / DEFAULT_PENDING_RETRIES_SUBDIR
        retry_dir.mkdir(parents=True)

        data = {
            "id": "2026-03-12_10-00-00_test",
            "status": "pending",
            "user_request": "Do something",
            "intended_action": "use tool Z",
        }
        (retry_dir / "2026-03-12_10-00-00_test.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        ctx = self._make_ctx(tmp_path)
        result = _list_pending_retries(ctx)
        assert "Pending retries (1):" in result
        assert "2026-03-12_10-00-00_test" in result
        assert "Do something" in result
        assert "use tool Z" in result

    def test_list_retries_skips_completed(self, tmp_path, monkeypatch) -> None:
        feedback_dir = tmp_path / "feedback"
        monkeypatch.setenv("FEEDBACK_DIR", str(feedback_dir))
        retry_dir = feedback_dir / DEFAULT_PENDING_RETRIES_SUBDIR
        retry_dir.mkdir(parents=True)

        completed = {
            "id": "done_task",
            "status": "completed",
            "user_request": "Old task",
            "intended_action": "old action",
        }
        (retry_dir / "done_task.json").write_text(
            json.dumps(completed), encoding="utf-8"
        )
        ctx = self._make_ctx(tmp_path)
        result = _list_pending_retries(ctx)
        assert result == "No pending retries found."

    def test_list_retries_handles_corrupt_json(self, tmp_path, monkeypatch) -> None:
        feedback_dir = tmp_path / "feedback"
        monkeypatch.setenv("FEEDBACK_DIR", str(feedback_dir))
        retry_dir = feedback_dir / DEFAULT_PENDING_RETRIES_SUBDIR
        retry_dir.mkdir(parents=True)

        (retry_dir / "bad.json").write_text("not valid json{{{", encoding="utf-8")
        ctx = self._make_ctx(tmp_path)
        result = _list_pending_retries(ctx)
        assert result == "No pending retries found."


class TestCompleteRetry:
    def _make_ctx(self, tmp_path):
        settings = make_test_settings()
        deps = Deps(
            memory=MemoryStore(str(tmp_path / "mem.json")),
            settings=settings,
            user_id="tester@test.com",
            plugin_data={},
        )
        ctx = MagicMock(spec=RunContext)
        ctx.deps = deps
        return ctx

    def test_complete_success(self, tmp_path, monkeypatch) -> None:
        feedback_dir = tmp_path / "feedback"
        monkeypatch.setenv("FEEDBACK_DIR", str(feedback_dir))
        retry_dir = feedback_dir / DEFAULT_PENDING_RETRIES_SUBDIR
        retry_dir.mkdir(parents=True)

        data = {
            "id": "retry_1",
            "status": "pending",
            "user_request": "Do X",
            "intended_action": "tool Y",
            "completed_at": None,
        }
        retry_file = retry_dir / "retry_1.json"
        retry_file.write_text(json.dumps(data), encoding="utf-8")

        ctx = self._make_ctx(tmp_path)
        result = _complete_retry(ctx, "retry_1")
        assert result == "Retry completed: retry_1"

        updated = json.loads(retry_file.read_text(encoding="utf-8"))
        assert updated["status"] == "completed"
        assert updated["completed_at"] is not None

    def test_complete_not_found(self, tmp_path, monkeypatch) -> None:
        feedback_dir = tmp_path / "feedback"
        monkeypatch.setenv("FEEDBACK_DIR", str(feedback_dir))
        ctx = self._make_ctx(tmp_path)
        result = _complete_retry(ctx, "nonexistent")
        assert result == "Retry not found: nonexistent"

    def test_complete_already_completed(self, tmp_path, monkeypatch) -> None:
        feedback_dir = tmp_path / "feedback"
        monkeypatch.setenv("FEEDBACK_DIR", str(feedback_dir))
        retry_dir = feedback_dir / DEFAULT_PENDING_RETRIES_SUBDIR
        retry_dir.mkdir(parents=True)

        data = {
            "id": "retry_done",
            "status": "completed",
            "completed_at": "2026-03-12T10:00:00+00:00",
        }
        (retry_dir / "retry_done.json").write_text(json.dumps(data), encoding="utf-8")

        ctx = self._make_ctx(tmp_path)
        result = _complete_retry(ctx, "retry_done")
        assert result == "Retry already completed: retry_done"


class TestSynonymTools:
    def _make_ctx(self, tmp_path):
        settings = make_test_settings()
        deps = Deps(
            memory=MemoryStore(str(tmp_path / "mem.json")),
            settings=settings,
            user_id="tester@test.com",
            plugin_data={},
        )
        ctx = MagicMock(spec=RunContext)
        ctx.deps = deps
        return ctx

    def test_add_synonym_stores_with_prefix(self, tmp_path) -> None:
        ctx = self._make_ctx(tmp_path)
        result = _add_synonym(ctx, "löschen", "clear")
        assert "löschen" in result
        assert "clear" in result
        assert ctx.deps.memory.get(f"{SYNONYM_PREFIX}löschen") == "clear"

    def test_list_synonyms_returns_formatted(self, tmp_path) -> None:
        ctx = self._make_ctx(tmp_path)
        ctx.deps.memory.set(f"{SYNONYM_PREFIX}löschen", "clear")
        ctx.deps.memory.set(f"{SYNONYM_PREFIX}neustart", "restart")

        result = _list_synonyms(ctx)
        assert "löschen → clear" in result
        assert "neustart → restart" in result

    def test_list_synonyms_empty(self, tmp_path) -> None:
        ctx = self._make_ctx(tmp_path)
        result = _list_synonyms(ctx)
        assert result == "No synonyms defined."

    def test_list_synonyms_excludes_non_synonym_entries(self, tmp_path) -> None:
        ctx = self._make_ctx(tmp_path)
        ctx.deps.memory.set("contact:alice", "alice@example.com")
        ctx.deps.memory.set(f"{SYNONYM_PREFIX}löschen", "clear")

        result = _list_synonyms(ctx)
        assert "löschen → clear" in result
        assert "alice" not in result

    def test_delete_synonym_existing(self, tmp_path) -> None:
        ctx = self._make_ctx(tmp_path)
        ctx.deps.memory.set(f"{SYNONYM_PREFIX}löschen", "clear")

        result = _delete_synonym(ctx, "löschen")
        assert "deleted" in result.lower()
        assert ctx.deps.memory.get(f"{SYNONYM_PREFIX}löschen") is None

    def test_delete_synonym_missing(self, tmp_path) -> None:
        ctx = self._make_ctx(tmp_path)
        result = _delete_synonym(ctx, "nonexistent")
        assert "No synonym found" in result

    def test_agent_includes_synonym_tools(self, tmp_memory_file: str) -> None:
        memory = MemoryStore(tmp_memory_file)
        registry = PluginRegistry()
        agent = create_agent(registry, memory, TestModel())
        tool_names = {t.name for t in agent._function_toolset.tools.values()}
        assert "add_synonym" in tool_names
        assert "list_synonyms" in tool_names
        assert "delete_synonym" in tool_names

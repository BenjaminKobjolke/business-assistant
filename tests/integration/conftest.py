"""Shared fixtures and helpers for integration tests."""

from __future__ import annotations

import contextlib
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic_ai import Agent

from business_assistant.config.constants import (
    DEFAULT_USAGE_LOG_DIR,
    USAGE_SOURCE_TEST,
)
from business_assistant.config.settings import AppSettings, OpenAISettings, XmppSettings
from business_assistant.usage.tracker import UsageTracker

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class FakeRawMessage:
    """Minimal stand-in for imap-client-lib raw message headers."""

    def __init__(self, headers: dict[str, str] | None = None) -> None:
        self._headers = headers or {}

    def get(self, key: str, default: str = "") -> str:
        return self._headers.get(key, default)


class FakeEmailMessage:
    """Minimal stand-in for imap-client-lib EmailMessage."""

    def __init__(
        self,
        message_id: str = "123",
        from_address: str = "sender@example.com",
        to_address: str = "",
        subject: str = "Test Subject",
        date: str = "Mon, 09 Mar 2026 10:00:00 +0100",
        body_plain: str = "Hello, this is a test email.",
        body_html: str = "",
        attachments: list | None = None,
    ):
        self.message_id = message_id
        self.from_address = from_address
        self.subject = subject
        self.date = date
        self._body_plain = body_plain
        self._body_html = body_html
        self.attachments = attachments or []
        self.raw_message = FakeRawMessage(
            {"To": to_address, "From": from_address}
        )

    def get_body(self, content_type: str = "text/plain") -> str | None:
        if content_type == "text/plain":
            return self._body_plain
        if content_type == "text/html":
            return self._body_html
        return None


def make_integration_settings(tmp_path: Path) -> AppSettings:
    """Create AppSettings for integration tests using real OpenAI keys."""
    memory_file = str(tmp_path / "memory.json")
    return AppSettings(
        xmpp=XmppSettings(
            jid="bot@example.com",
            password="secret",
            default_receiver="user@example.com",
            allowed_jids=["user@example.com"],
        ),
        openai=OpenAISettings(
            api_key=os.environ["OPENAI_API_KEY"],
            model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
        ),
        memory_file=memory_file,
        chat_log_file=str(tmp_path / "chat.log"),
        plugin_names=["business_assistant_imap"],
        max_conversation_history=100,
    )


@pytest.fixture(autouse=True, scope="session")
def _track_test_usage():
    """Automatically log API usage from integration test agent.run_sync() calls."""
    tracker = UsageTracker(
        str(_PROJECT_ROOT / DEFAULT_USAGE_LOG_DIR),
        tool_plugin_map={},
    )
    model_name = os.environ.get("OPENAI_MODEL", "gpt-4o")

    original_run_sync = Agent.run_sync

    def _wrapped_run_sync(self_agent, *args, **kwargs):
        result = original_run_sync(self_agent, *args, **kwargs)
        with contextlib.suppress(Exception):
            tracker.log(
                result.usage(),
                result.all_messages(),
                user="integration-test",
                model=model_name,
                source=USAGE_SOURCE_TEST,
            )
        return result

    with patch.object(Agent, "run_sync", _wrapped_run_sync):
        yield

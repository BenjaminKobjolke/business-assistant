"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from business_assistant.config.settings import AppSettings, OpenAISettings, XmppSettings
from business_assistant.memory.store import MemoryStore


@pytest.fixture()
def tmp_memory_file(tmp_path: Path) -> str:
    """Return path to a temporary memory JSON file."""
    return str(tmp_path / "memory.json")


@pytest.fixture()
def memory_store(tmp_memory_file: str) -> MemoryStore:
    """Create a MemoryStore backed by a temporary file."""
    return MemoryStore(tmp_memory_file)


def make_test_settings(
    chat_log_file: str = "data/chat.log",
    chat_log_dir: str = "logs/chat",
) -> AppSettings:
    """Create AppSettings for tests with customizable fields."""
    return AppSettings(
        xmpp=XmppSettings(
            jid="bot@test.com",
            password="pass",
            default_receiver="user@test.com",
            allowed_jids=["user@test.com"],
        ),
        openai=OpenAISettings(api_key="sk-test", model="gpt-4o"),
        memory_file="data/memory.json",
        chat_log_file=chat_log_file,
        chat_log_dir=chat_log_dir,
        usage_log_dir="logs/app/usage",
        plugin_names=[],
    )

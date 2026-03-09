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


@pytest.fixture()
def mock_settings() -> AppSettings:
    """Return a mock AppSettings instance."""
    return AppSettings(
        xmpp=XmppSettings(
            jid="bot@example.com",
            password="secret",
            default_receiver="user@example.com",
            allowed_jids=["user@example.com"],
        ),
        openai=OpenAISettings(
            api_key="test-key",
            model="gpt-4o",
        ),
        memory_file="data/memory.json",
        chat_log_file="data/chat.log",
        plugin_names=["test_plugin"],
    )

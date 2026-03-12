"""Tests for settings loading."""

from __future__ import annotations

from unittest.mock import patch

from business_assistant.config.settings import load_settings


class TestSettings:
    def test_load_settings_from_env(self, monkeypatch) -> None:
        monkeypatch.setenv("XMPP_JID", "bot@test.com")
        monkeypatch.setenv("XMPP_PASSWORD", "pass123")
        monkeypatch.setenv("XMPP_DEFAULT_RECEIVER", "user@test.com")
        monkeypatch.setenv("XMPP_ALLOWED_JIDS", "user@test.com,admin@test.com")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
        monkeypatch.setenv("MEMORY_FILE", "/tmp/mem.json")
        monkeypatch.setenv("PLUGINS", "plugin_a,plugin_b")

        settings = load_settings()

        assert settings.xmpp.jid == "bot@test.com"
        assert settings.xmpp.password == "pass123"
        assert settings.xmpp.default_receiver == "user@test.com"
        assert settings.xmpp.allowed_jids == ["user@test.com", "admin@test.com"]
        assert settings.openai.api_key == "sk-test"
        assert settings.openai.model == "gpt-4o-mini"
        assert settings.memory_file == "/tmp/mem.json"
        assert settings.plugin_names == ["plugin_a", "plugin_b"]

    def test_load_settings_defaults(self, monkeypatch) -> None:
        for key in [
            "XMPP_JID", "XMPP_PASSWORD", "XMPP_DEFAULT_RECEIVER",
            "XMPP_ALLOWED_JIDS", "OPENAI_API_KEY", "OPENAI_MODEL",
            "MEMORY_FILE", "CHAT_LOG_FILE", "PLUGINS",
        ]:
            monkeypatch.delenv(key, raising=False)

        with patch("business_assistant.config.settings.load_dotenv"):
            settings = load_settings()

        assert settings.xmpp.jid == ""
        assert settings.openai.model == "gpt-4o"
        assert settings.memory_file == "data/memory.json"
        assert settings.chat_log_file == "data/chat.log"
        assert settings.usage_log_dir == "logs/app/usage"
        assert settings.plugin_names == []
        assert settings.max_conversation_history == 100

    def test_empty_plugins_string(self, monkeypatch) -> None:
        monkeypatch.setenv("PLUGINS", "")
        settings = load_settings()
        assert settings.plugin_names == []

    def test_plugins_with_whitespace(self, monkeypatch) -> None:
        monkeypatch.setenv("PLUGINS", " plugin_a , plugin_b , ")
        settings = load_settings()
        assert settings.plugin_names == ["plugin_a", "plugin_b"]

    def test_max_conversation_history_from_env(self, monkeypatch) -> None:
        monkeypatch.setenv("MAX_CONVERSATION_HISTORY", "50")
        settings = load_settings()
        assert settings.max_conversation_history == 50

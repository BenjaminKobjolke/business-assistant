"""Tests for startup greeting feature."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from business_assistant.config.constants import (
    DEFAULT_STARTUP_GREETING_MESSAGE,
)
from business_assistant.config.settings import load_settings


class TestStartupGreetingSettings:
    def test_greeting_disabled_by_default(self, monkeypatch) -> None:
        monkeypatch.delenv("STARTUP_GREETING_ENABLED", raising=False)
        monkeypatch.delenv("STARTUP_GREETING_MESSAGE", raising=False)

        with patch("business_assistant.config.settings.load_dotenv"):
            settings = load_settings()

        assert settings.startup_greeting_enabled is False
        assert settings.startup_greeting_message == DEFAULT_STARTUP_GREETING_MESSAGE

    def test_greeting_enabled(self, monkeypatch) -> None:
        monkeypatch.setenv("STARTUP_GREETING_ENABLED", "true")
        settings = load_settings()
        assert settings.startup_greeting_enabled is True

    def test_greeting_enabled_yes(self, monkeypatch) -> None:
        monkeypatch.setenv("STARTUP_GREETING_ENABLED", "yes")
        settings = load_settings()
        assert settings.startup_greeting_enabled is True

    def test_greeting_enabled_one(self, monkeypatch) -> None:
        monkeypatch.setenv("STARTUP_GREETING_ENABLED", "1")
        settings = load_settings()
        assert settings.startup_greeting_enabled is True

    def test_greeting_disabled_explicit(self, monkeypatch) -> None:
        monkeypatch.setenv("STARTUP_GREETING_ENABLED", "false")
        with patch("business_assistant.config.settings.load_dotenv"):
            settings = load_settings()
        assert settings.startup_greeting_enabled is False

    def test_custom_greeting_message(self, monkeypatch) -> None:
        monkeypatch.setenv("STARTUP_GREETING_MESSAGE", "Welcome!")
        settings = load_settings()
        assert settings.startup_greeting_message == "Welcome!"


class TestStartupGreetingApp:
    @patch("business_assistant.bot.app._load_credential_files")
    @patch("business_assistant.bot.app.load_settings")
    @patch("business_assistant.bot.app.MemoryStore")
    @patch("business_assistant.bot.app.load_plugins")
    @patch("business_assistant.bot.app.create_agent")
    @patch("business_assistant.bot.app.CategoryRouter")
    @patch("business_assistant.bot.app.get_core_tools")
    @patch("business_assistant.bot.app.UsageTracker")
    @patch("business_assistant.bot.app.FileDownloader")
    @patch("business_assistant.bot.app.AIMessageHandler")
    @patch("business_assistant.bot.app.SettingsConfigProvider")
    @patch("business_assistant.bot.app.BotManager")
    def test_greeting_sent_when_enabled(
        self,
        mock_bot_manager_cls,
        mock_config_provider,
        mock_handler,
        mock_downloader,
        mock_usage_tracker,
        mock_core_tools,
        mock_router,
        mock_create_agent,
        mock_load_plugins,
        mock_memory_store,
        mock_load_settings,
        mock_load_creds,
    ) -> None:
        from business_assistant.bot.app import Application
        from business_assistant.config.settings import (
            AppSettings,
            OpenAISettings,
            XmppSettings,
        )

        settings = AppSettings(
            xmpp=XmppSettings(
                jid="bot@test.com",
                password="pass",
                default_receiver="user@test.com",
                allowed_jids=["alice@test.com", "bob@test.com"],
            ),
            openai=OpenAISettings(api_key="sk-test", model="gpt-4o"),
            memory_file="data/memory.json",
            chat_log_file="data/chat.log",
            chat_log_dir="logs/chat",
            usage_log_dir="logs/app/usage",
            plugin_names=[],
            startup_greeting_enabled=True,
            startup_greeting_message="Hello there!",
        )
        mock_load_settings.return_value = settings

        mock_registry = MagicMock()
        mock_registry.tool_plugin_map.return_value = {}

        mock_bot_mgr = MagicMock()
        mock_bot_manager_cls.return_value = mock_bot_mgr

        app = Application()
        app.start()

        assert mock_bot_mgr.send_message.call_count == 2
        mock_bot_mgr.send_message.assert_any_call("alice@test.com", "Hello there!")
        mock_bot_mgr.send_message.assert_any_call("bob@test.com", "Hello there!")

    @patch("business_assistant.bot.app._load_credential_files")
    @patch("business_assistant.bot.app.load_settings")
    @patch("business_assistant.bot.app.MemoryStore")
    @patch("business_assistant.bot.app.load_plugins")
    @patch("business_assistant.bot.app.create_agent")
    @patch("business_assistant.bot.app.CategoryRouter")
    @patch("business_assistant.bot.app.get_core_tools")
    @patch("business_assistant.bot.app.UsageTracker")
    @patch("business_assistant.bot.app.FileDownloader")
    @patch("business_assistant.bot.app.AIMessageHandler")
    @patch("business_assistant.bot.app.SettingsConfigProvider")
    @patch("business_assistant.bot.app.BotManager")
    def test_greeting_skipped_when_disabled(
        self,
        mock_bot_manager_cls,
        mock_config_provider,
        mock_handler,
        mock_downloader,
        mock_usage_tracker,
        mock_core_tools,
        mock_router,
        mock_create_agent,
        mock_load_plugins,
        mock_memory_store,
        mock_load_settings,
        mock_load_creds,
    ) -> None:
        from business_assistant.bot.app import Application
        from business_assistant.config.settings import (
            AppSettings,
            OpenAISettings,
            XmppSettings,
        )

        settings = AppSettings(
            xmpp=XmppSettings(
                jid="bot@test.com",
                password="pass",
                default_receiver="user@test.com",
                allowed_jids=["alice@test.com"],
            ),
            openai=OpenAISettings(api_key="sk-test", model="gpt-4o"),
            memory_file="data/memory.json",
            chat_log_file="data/chat.log",
            chat_log_dir="logs/chat",
            usage_log_dir="logs/app/usage",
            plugin_names=[],
            startup_greeting_enabled=False,
        )
        mock_load_settings.return_value = settings

        mock_registry = MagicMock()
        mock_registry.tool_plugin_map.return_value = {}

        mock_bot_mgr = MagicMock()
        mock_bot_manager_cls.return_value = mock_bot_mgr

        app = Application()
        app.start()

        mock_bot_mgr.send_message.assert_not_called()

    @patch("business_assistant.bot.app._load_credential_files")
    @patch("business_assistant.bot.app.load_settings")
    @patch("business_assistant.bot.app.MemoryStore")
    @patch("business_assistant.bot.app.load_plugins")
    @patch("business_assistant.bot.app.create_agent")
    @patch("business_assistant.bot.app.CategoryRouter")
    @patch("business_assistant.bot.app.get_core_tools")
    @patch("business_assistant.bot.app.UsageTracker")
    @patch("business_assistant.bot.app.FileDownloader")
    @patch("business_assistant.bot.app.AIMessageHandler")
    @patch("business_assistant.bot.app.SettingsConfigProvider")
    @patch("business_assistant.bot.app.BotManager")
    def test_greeting_skipped_when_no_allowed_jids(
        self,
        mock_bot_manager_cls,
        mock_config_provider,
        mock_handler,
        mock_downloader,
        mock_usage_tracker,
        mock_core_tools,
        mock_router,
        mock_create_agent,
        mock_load_plugins,
        mock_memory_store,
        mock_load_settings,
        mock_load_creds,
    ) -> None:
        from business_assistant.bot.app import Application
        from business_assistant.config.settings import (
            AppSettings,
            OpenAISettings,
            XmppSettings,
        )

        settings = AppSettings(
            xmpp=XmppSettings(
                jid="bot@test.com",
                password="pass",
                default_receiver="user@test.com",
                allowed_jids=[],
            ),
            openai=OpenAISettings(api_key="sk-test", model="gpt-4o"),
            memory_file="data/memory.json",
            chat_log_file="data/chat.log",
            chat_log_dir="logs/chat",
            usage_log_dir="logs/app/usage",
            plugin_names=[],
            startup_greeting_enabled=True,
        )
        mock_load_settings.return_value = settings

        mock_registry = MagicMock()
        mock_registry.tool_plugin_map.return_value = {}

        mock_bot_mgr = MagicMock()
        mock_bot_manager_cls.return_value = mock_bot_mgr

        app = Application()
        app.start()

        mock_bot_mgr.send_message.assert_not_called()

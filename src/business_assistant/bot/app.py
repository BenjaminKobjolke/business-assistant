"""Application lifecycle — wires settings, plugins, agent, and bot together."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from bot_commander.manager import BotManager

from business_assistant.agent.agent import create_agent, get_core_tools
from business_assistant.agent.router import CategoryRouter
from business_assistant.config.constants import (
    BOT_TYPE_XMPP,
    CORE_PLUGIN_NAME,
    CREDENTIAL_DIR,
    ENV_RTM_TOKEN,
    LOG_APP_STARTING,
    LOG_APP_STOPPED,
    PLUGIN_DATA_COMMAND_HANDLERS,
    PLUGIN_DATA_FTP_SERVICE,
    RTM_TOKEN_FILE,
)
from business_assistant.config.settings import load_settings
from business_assistant.files.downloader import FileDownloader
from business_assistant.memory.store import MemoryStore
from business_assistant.plugins.loader import load_plugins
from business_assistant.plugins.registry import PluginRegistry
from business_assistant.usage.command import create_usage_handler
from business_assistant.usage.tracker import UsageTracker

from .config_provider import SettingsConfigProvider
from .handler import AIMessageHandler

logger = logging.getLogger(__name__)

# Mapping of credential files to env var names.
_CREDENTIAL_FILES: dict[str, str] = {
    RTM_TOKEN_FILE: ENV_RTM_TOKEN,
}


def _load_credential_files(project_root: Path | None = None) -> None:
    """Load auto-generated credential files from data/ into environment variables.

    Only sets a variable if the file exists and the variable is not already set.
    """
    if project_root is None:
        project_root = Path(__file__).resolve().parents[3]
    cred_dir = project_root / CREDENTIAL_DIR

    for filename, env_var in _CREDENTIAL_FILES.items():
        if os.environ.get(env_var):
            continue
        filepath = cred_dir / filename
        if filepath.is_file():
            value = filepath.read_text(encoding="utf-8").strip()
            if value:
                os.environ[env_var] = value
                logger.info("Loaded %s from %s", env_var, filepath)


class Application:
    """Main application — orchestrates startup, wiring, and shutdown."""

    def __init__(self) -> None:
        self._bot_manager: BotManager | None = None

    def start(self) -> None:
        """Load settings, plugins, create agent, and start the XMPP bot."""
        logger.info(LOG_APP_STARTING)

        _load_credential_files()

        settings = load_settings()
        utc_now = datetime.now(tz=UTC)
        local_now = utc_now.astimezone(ZoneInfo(settings.timezone))
        logger.info(
            "System clock: utc=%s, local=%s (%s)",
            utc_now.strftime("%Y-%m-%d %H:%M:%S UTC"),
            local_now.strftime("%Y-%m-%d %H:%M:%S %Z"),
            settings.timezone,
        )
        memory = MemoryStore(settings.memory_file)

        plugin_data: dict = {
            PLUGIN_DATA_COMMAND_HANDLERS: [create_usage_handler(settings)],
        }

        if settings.ftp:
            from business_assistant.upload.ftp_service import FtpUploadService

            plugin_data[PLUGIN_DATA_FTP_SERVICE] = FtpUploadService(settings.ftp)

        registry = PluginRegistry(plugin_data=plugin_data)
        load_plugins(registry, settings.plugin_names)

        model_name = f"openai:{settings.openai.model}"
        agent = create_agent(
            registry, memory, model_name,
            timezone=settings.timezone, core_only=True,
        )

        if settings.openai.router_api_base_url:
            from pydantic_ai.models.openai import OpenAIChatModel
            from pydantic_ai.providers.openai import OpenAIProvider

            router_provider = OpenAIProvider(
                base_url=settings.openai.router_api_base_url,
                api_key=settings.openai.router_api_key or settings.openai.api_key,
            )
            router_model: Any = OpenAIChatModel(
                settings.openai.router_model, provider=router_provider,
            )
        else:
            router_model = f"openai:{settings.openai.router_model}"

        router = CategoryRouter(
            registry, model=router_model, model_name=settings.openai.router_model,
        )
        core_tools = get_core_tools()

        tool_plugin_map = registry.tool_plugin_map()
        for name in (
            "memory_get",
            "memory_set",
            "memory_delete",
            "memory_list",
            "write_feedback",
            "list_pending_retries",
            "complete_retry",
            "add_synonym",
            "list_synonyms",
            "delete_synonym",
        ):
            tool_plugin_map[name] = CORE_PLUGIN_NAME
        usage_tracker = UsageTracker(settings.usage_log_dir, tool_plugin_map)
        downloader = FileDownloader(settings.upload_dir)

        handler = AIMessageHandler(
            agent=agent,
            memory=memory,
            settings=settings,
            plugin_data=plugin_data,
            usage_tracker=usage_tracker,
            model_name=settings.openai.model,
            file_downloader=downloader,
            registry=registry,
            router=router,
            core_tools=core_tools,
        )

        config_provider = SettingsConfigProvider(settings.xmpp)
        self._bot_manager = BotManager(
            message_handler=handler,
            config_provider=config_provider,
            bot_type=BOT_TYPE_XMPP,
        )
        self._bot_manager.start()

    def shutdown(self) -> None:
        """Shut down the bot and reset the XMPP singleton for restart."""
        if self._bot_manager:
            self._bot_manager.shutdown()
        _reset_xmpp_singleton()
        logger.info(LOG_APP_STOPPED)


def _reset_xmpp_singleton() -> None:
    """Reset the XmppBot singleton so a fresh start() can re-initialize."""
    with contextlib.suppress(Exception):
        from xmpp_bot.bot import XmppBot

        asyncio.run(XmppBot.reset_instance())

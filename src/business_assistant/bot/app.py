"""Application lifecycle — wires settings, plugins, agent, and bot together."""

from __future__ import annotations

import asyncio
import contextlib
import logging

from bot_commander.manager import BotManager

from business_assistant.agent.agent import create_agent
from business_assistant.config.constants import BOT_TYPE_XMPP, LOG_APP_STARTING, LOG_APP_STOPPED
from business_assistant.config.settings import load_settings
from business_assistant.memory.store import MemoryStore
from business_assistant.plugins.loader import load_plugins
from business_assistant.plugins.registry import PluginRegistry

from .config_provider import SettingsConfigProvider
from .handler import AIMessageHandler

logger = logging.getLogger(__name__)


class Application:
    """Main application — orchestrates startup, wiring, and shutdown."""

    def __init__(self) -> None:
        self._bot_manager: BotManager | None = None

    def start(self) -> None:
        """Load settings, plugins, create agent, and start the XMPP bot."""
        logger.info(LOG_APP_STARTING)

        settings = load_settings()
        memory = MemoryStore(settings.memory_file)

        plugin_data: dict = {}
        registry = PluginRegistry(plugin_data=plugin_data)
        load_plugins(registry, settings.plugin_names)

        model_name = f"openai:{settings.openai.model}"
        agent = create_agent(registry, memory, model_name)

        handler = AIMessageHandler(
            agent=agent,
            memory=memory,
            settings=settings,
            plugin_data=plugin_data,
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

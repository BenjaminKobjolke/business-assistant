"""BotConfigProvider adapter mapping AppSettings to bot-commander config keys."""

from __future__ import annotations

from business_assistant.config.constants import (
    BOT_CFG_ALLOWED_JIDS,
    BOT_CFG_DEFAULT_RECEIVER,
    BOT_CFG_JID,
    BOT_CFG_PASSWORD,
)
from business_assistant.config.settings import XmppSettings


class SettingsConfigProvider:
    """Implements the BotConfigProvider protocol for bot-commander.

    Maps get_bot_setting(key) calls to XmppSettings fields.
    """

    def __init__(self, xmpp: XmppSettings) -> None:
        self._xmpp = xmpp
        self._mapping: dict[str, str] = {
            BOT_CFG_JID: xmpp.jid,
            BOT_CFG_PASSWORD: xmpp.password,
            BOT_CFG_DEFAULT_RECEIVER: xmpp.default_receiver,
            BOT_CFG_ALLOWED_JIDS: ",".join(xmpp.allowed_jids),
        }

    def get_bot_setting(self, key: str, fallback: str = "") -> str:
        """Return a bot setting by key, with optional fallback."""
        return self._mapping.get(key, fallback)

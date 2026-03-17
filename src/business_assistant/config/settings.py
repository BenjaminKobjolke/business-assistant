"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from .constants import (
    DEFAULT_CHAT_LOG_DIR,
    DEFAULT_CHAT_LOG_FILE,
    DEFAULT_FTP_PORT,
    DEFAULT_MAX_CONVERSATION_HISTORY,
    DEFAULT_MEMORY_FILE,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_ROUTER_MODEL,
    DEFAULT_STARTUP_GREETING_MESSAGE,
    DEFAULT_UPLOAD_DIR,
    DEFAULT_USAGE_LOG_DIR,
    DEFAULT_USER_TIMEZONE,
    ENV_CHAT_LOG_DIR,
    ENV_CHAT_LOG_FILE,
    ENV_FTP_BASE_PATH,
    ENV_FTP_BASE_URL,
    ENV_FTP_HOST,
    ENV_FTP_PASSWORD,
    ENV_FTP_PORT,
    ENV_FTP_USE_TLS,
    ENV_FTP_USERNAME,
    ENV_MAX_CONVERSATION_HISTORY,
    ENV_MEMORY_FILE,
    ENV_OPENAI_API_KEY,
    ENV_OPENAI_MODEL,
    ENV_PLUGINS,
    ENV_ROUTER_API_BASE_URL,
    ENV_ROUTER_API_KEY,
    ENV_ROUTER_MODEL,
    ENV_STARTUP_GREETING_ENABLED,
    ENV_STARTUP_GREETING_MESSAGE,
    ENV_UPLOAD_DIR,
    ENV_USAGE_LOG_DIR,
    ENV_USER_TIMEZONE,
    ENV_XMPP_ALLOWED_JIDS,
    ENV_XMPP_DEFAULT_RECEIVER,
    ENV_XMPP_JID,
    ENV_XMPP_PASSWORD,
)


@dataclass(frozen=True)
class XmppSettings:
    """XMPP connection settings."""

    jid: str
    password: str
    default_receiver: str
    allowed_jids: list[str]


@dataclass(frozen=True)
class OpenAISettings:
    """OpenAI API settings."""

    api_key: str
    model: str
    router_model: str = DEFAULT_ROUTER_MODEL
    router_api_key: str = ""
    router_api_base_url: str = ""


@dataclass(frozen=True)
class FtpSettings:
    """FTP upload settings."""

    host: str
    username: str
    password: str
    base_path: str
    base_url: str
    port: int = DEFAULT_FTP_PORT
    use_tls: bool = True


@dataclass(frozen=True)
class AppSettings:
    """Top-level application settings."""

    xmpp: XmppSettings
    openai: OpenAISettings
    memory_file: str
    chat_log_file: str
    chat_log_dir: str
    usage_log_dir: str
    plugin_names: list[str]
    timezone: str = DEFAULT_USER_TIMEZONE
    upload_dir: str = DEFAULT_UPLOAD_DIR
    max_conversation_history: int = DEFAULT_MAX_CONVERSATION_HISTORY
    startup_greeting_enabled: bool = False
    startup_greeting_message: str = DEFAULT_STARTUP_GREETING_MESSAGE
    ftp: FtpSettings | None = None


def load_settings() -> AppSettings:
    """Load settings from environment variables.

    Calls dotenv.load_dotenv() to pick up .env files.
    """
    load_dotenv()

    xmpp = XmppSettings(
        jid=os.environ.get(ENV_XMPP_JID, ""),
        password=os.environ.get(ENV_XMPP_PASSWORD, ""),
        default_receiver=os.environ.get(ENV_XMPP_DEFAULT_RECEIVER, ""),
        allowed_jids=[
            jid.strip()
            for jid in os.environ.get(ENV_XMPP_ALLOWED_JIDS, "").split(",")
            if jid.strip()
        ],
    )

    openai = OpenAISettings(
        api_key=os.environ.get(ENV_OPENAI_API_KEY, ""),
        model=os.environ.get(ENV_OPENAI_MODEL, DEFAULT_OPENAI_MODEL),
        router_model=os.environ.get(ENV_ROUTER_MODEL, DEFAULT_ROUTER_MODEL),
        router_api_key=os.environ.get(ENV_ROUTER_API_KEY, ""),
        router_api_base_url=os.environ.get(ENV_ROUTER_API_BASE_URL, ""),
    )

    raw_plugins = os.environ.get(ENV_PLUGINS, "")
    plugin_names = [name.strip() for name in raw_plugins.split(",") if name.strip()]

    ftp: FtpSettings | None = None
    ftp_host = os.environ.get(ENV_FTP_HOST, "")
    if ftp_host:
        ftp = FtpSettings(
            host=ftp_host,
            username=os.environ.get(ENV_FTP_USERNAME, ""),
            password=os.environ.get(ENV_FTP_PASSWORD, ""),
            base_path=os.environ.get(ENV_FTP_BASE_PATH, ""),
            base_url=os.environ.get(ENV_FTP_BASE_URL, ""),
            port=int(os.environ.get(ENV_FTP_PORT, str(DEFAULT_FTP_PORT))),
            use_tls=os.environ.get(ENV_FTP_USE_TLS, "true").lower() in ("true", "1", "yes"),
        )

    return AppSettings(
        xmpp=xmpp,
        openai=openai,
        memory_file=os.environ.get(ENV_MEMORY_FILE, DEFAULT_MEMORY_FILE),
        chat_log_file=os.environ.get(ENV_CHAT_LOG_FILE, DEFAULT_CHAT_LOG_FILE),
        chat_log_dir=os.environ.get(ENV_CHAT_LOG_DIR, DEFAULT_CHAT_LOG_DIR),
        usage_log_dir=os.environ.get(ENV_USAGE_LOG_DIR, DEFAULT_USAGE_LOG_DIR),
        timezone=os.environ.get(ENV_USER_TIMEZONE, DEFAULT_USER_TIMEZONE),
        upload_dir=os.environ.get(ENV_UPLOAD_DIR, DEFAULT_UPLOAD_DIR),
        plugin_names=plugin_names,
        max_conversation_history=int(
            os.environ.get(
                ENV_MAX_CONVERSATION_HISTORY,
                str(DEFAULT_MAX_CONVERSATION_HISTORY),
            )
        ),
        startup_greeting_enabled=os.environ.get(
            ENV_STARTUP_GREETING_ENABLED, ""
        ).lower()
        in ("true", "1", "yes"),
        startup_greeting_message=os.environ.get(
            ENV_STARTUP_GREETING_MESSAGE, DEFAULT_STARTUP_GREETING_MESSAGE
        ),
        ftp=ftp,
    )

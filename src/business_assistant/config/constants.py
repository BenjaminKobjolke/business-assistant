"""Centralized string constants for the business assistant."""

# Environment variable names
ENV_XMPP_JID = "XMPP_JID"
ENV_XMPP_PASSWORD = "XMPP_PASSWORD"
ENV_XMPP_DEFAULT_RECEIVER = "XMPP_DEFAULT_RECEIVER"
ENV_XMPP_ALLOWED_JIDS = "XMPP_ALLOWED_JIDS"
ENV_OPENAI_API_KEY = "OPENAI_API_KEY"
ENV_OPENAI_MODEL = "OPENAI_MODEL"
ENV_MEMORY_FILE = "MEMORY_FILE"
ENV_PLUGINS = "PLUGINS"
ENV_CHAT_LOG_FILE = "CHAT_LOG_FILE"
ENV_MAX_CONVERSATION_HISTORY = "MAX_CONVERSATION_HISTORY"

# Defaults
DEFAULT_OPENAI_MODEL = "gpt-4o"
DEFAULT_MEMORY_FILE = "data/memory.json"
DEFAULT_CHAT_LOG_FILE = "data/chat.log"
DEFAULT_MAX_CONVERSATION_HISTORY = 100

# Bot config keys (used by BotConfigProvider)
BOT_CFG_JID = "jid"
BOT_CFG_PASSWORD = "password"
BOT_CFG_DEFAULT_RECEIVER = "default_receiver"
BOT_CFG_ALLOWED_JIDS = "allowed_jids"

# Bot type
BOT_TYPE_XMPP = "xmpp"

# Error messages
ERR_AGENT_FAILED = "Sorry, I encountered an error processing your message. Please try again."
ERR_PLUGIN_LOAD_FAILED = "Failed to load plugin: {name}"

# Log messages
LOG_PLUGIN_LOADED = "Loaded plugin: {name}"
LOG_PLUGIN_FAILED = "Failed to load plugin: {name}"
LOG_APP_STARTING = "Starting Business Assistant v2"
LOG_APP_STOPPED = "Business Assistant v2 stopped"
LOG_AGENT_ERROR = "Error running AI agent"

# System prompt
SYSTEM_PROMPT_BASE = """You are a helpful business assistant. You help users manage their work \
by interacting with various business tools like email, calendar, and more.

You communicate via XMPP chat. Keep responses concise and well-formatted for chat.

When a user mentions a person's name, check your memory for any stored aliases or contact \
information before performing searches.

Current memory contents:
{memory_contents}

{plugin_extras}"""

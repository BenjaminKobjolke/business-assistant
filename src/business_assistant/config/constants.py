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
ENV_USER_TIMEZONE = "USER_TIMEZONE"
ENV_CHAT_LOG_FILE = "CHAT_LOG_FILE"
ENV_MAX_CONVERSATION_HISTORY = "MAX_CONVERSATION_HISTORY"

# Defaults
DEFAULT_OPENAI_MODEL = "gpt-4o"
DEFAULT_USER_TIMEZONE = "Europe/Berlin"
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

# Chat commands (matched case-insensitive)
CMD_CLEAR = {"clear", "clear chat", "clear chat history"}
CMD_RESTART = {"restart", "restart chat"}

# Command responses
RESP_CHAT_CLEARED = "Chat history cleared."
RESP_RESTART_TRIGGERED = "Restarting... please wait a moment."

# Restart / Shutdown
RESTART_FLAG_FILE = "restart.flag"
SHUTDOWN_FLAG_FILE = "shutdown.flag"

# Credential files (auto-generated tokens stored in data/)
CREDENTIAL_DIR = "data"
RTM_TOKEN_FILE = "rtm_token"
ENV_RTM_TOKEN = "RTM_TOKEN"

# Feedback
DEFAULT_FEEDBACK_DIR = "feedback"
ENV_FEEDBACK_DIR = "FEEDBACK_DIR"

# Pending retries
DEFAULT_PENDING_RETRIES_SUBDIR = "pending_retries"
RETRY_STATUS_PENDING = "pending"
RETRY_STATUS_COMPLETED = "completed"

# File uploads
DEFAULT_UPLOAD_DIR = "data/uploads"
ENV_UPLOAD_DIR = "UPLOAD_DIR"
PLUGIN_DATA_FILE_HANDLERS = "file_handlers"

# Response processors
PLUGIN_DATA_RESPONSE_PROCESSORS = "response_processors"

# Command handlers (plugin-registered, run before AI)
PLUGIN_DATA_COMMAND_HANDLERS = "command_handlers"

# Message modifiers (modify text before AI processes it)
PLUGIN_DATA_MESSAGE_MODIFIERS = "message_modifiers"

# FTP environment variables
ENV_FTP_HOST = "FTP_HOST"
ENV_FTP_USERNAME = "FTP_USERNAME"
ENV_FTP_PASSWORD = "FTP_PASSWORD"
ENV_FTP_PORT = "FTP_PORT"
ENV_FTP_USE_TLS = "FTP_USE_TLS"
ENV_FTP_BASE_PATH = "FTP_BASE_PATH"
ENV_FTP_BASE_URL = "FTP_BASE_URL"

# FTP defaults
DEFAULT_FTP_PORT = 21

# Plugin data key
PLUGIN_DATA_FTP_SERVICE = "ftp_upload"

# Usage tracking
ENV_USAGE_LOG_DIR = "USAGE_LOG_DIR"
DEFAULT_USAGE_LOG_DIR = "logs/app/usage"
USAGE_LOG_PREFIX = "usage"
USAGE_LOG_SUFFIX = ".jsonl"
CORE_PLUGIN_NAME = "core"

# Logging environment variables
ENV_LOG_LEVEL = "LOG_LEVEL"
ENV_LOG_DIR = "LOG_DIR"
ENV_LOG_BACKUP_COUNT = "LOG_BACKUP_COUNT"

# Plugin categories
CATEGORY_TODO = "todo"
CATEGORY_EMAIL = "email"
CATEGORY_CALENDAR = "calendar"
CATEGORY_PROJECT_MANAGEMENT = "project_management"

# Logging defaults
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_DIR = "logs"
DEFAULT_LOG_BACKUP_COUNT = 3
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# Log messages
LOG_PLUGIN_LOADED = "Loaded plugin: {name}"
LOG_PLUGIN_FAILED = "Failed to load plugin: {name}"
LOG_APP_STARTING = "Starting Business Assistant v2"
LOG_APP_STOPPED = "Business Assistant v2 stopped"
LOG_APP_RESTARTING = "Restart requested via restart.flag — restarting..."
LOG_APP_SHUTDOWN_FLAG = "Shutdown requested via shutdown.flag — stopping..."
LOG_AGENT_ERROR = "Error running AI agent"
LOG_FILE_DOWNLOADED = "Downloaded file: %s (%d bytes)"
LOG_FILE_DOWNLOAD_FAILED = "Failed to download file from %s"

# System prompt
SYSTEM_PROMPT_BASE = """You are a helpful business assistant. You help users manage their work \
by interacting with various business tools like email, calendar, and more.

You communicate via XMPP chat. Keep responses concise and well-formatted for chat.

When a user mentions a person's name, check your memory for any stored aliases or contact \
information before performing searches.

If you encounter a problem with a tool (e.g. a function returns an error, unexpected behavior, \
or you cannot fulfill a request due to tool limitations), use the write_feedback tool to document \
the issue for the developer. Include what you tried, what happened, and what you expected.

When you cannot fulfill a user request due to a missing tool or capability, use write_feedback \
with the intended_action parameter to save a pending retry. Describe the user's original request \
in the content and what tool or action would be needed in intended_action. \
Periodically (or when a user asks), check list_pending_retries to see if any previously failed \
actions can now be fulfilled with your current tools. If you can complete a pending retry, \
execute the action and then call complete_retry with the retry ID.

When calling tools that require no parameters, pass an empty arguments object {{}}. \
Do not use {{"_":{{}}}} or any other wrapper.

Current memory contents:
{memory_contents}

{plugin_extras}"""

"""Centralized string constants for the business assistant."""

# Environment variable names
ENV_XMPP_JID = "XMPP_JID"
ENV_XMPP_PASSWORD = "XMPP_PASSWORD"
ENV_XMPP_DEFAULT_RECEIVER = "XMPP_DEFAULT_RECEIVER"
ENV_XMPP_ALLOWED_JIDS = "XMPP_ALLOWED_JIDS"
ENV_OPENAI_API_KEY = "OPENAI_API_KEY"
ENV_OPENAI_API_BASE_URL = "OPENAI_API_BASE_URL"
ENV_OPENAI_MODEL = "OPENAI_MODEL"
ENV_ROUTER_MODEL = "ROUTER_MODEL"
ENV_ROUTER_API_KEY = "ROUTER_API_KEY"
ENV_ROUTER_API_BASE_URL = "ROUTER_API_BASE_URL"
ENV_OLLAMA_BASE_URL = "OLLAMA_BASE_URL"
ENV_MEMORY_FILE = "MEMORY_FILE"
ENV_PLUGINS = "PLUGINS"
ENV_USER_TIMEZONE = "USER_TIMEZONE"
ENV_CHAT_LOG_FILE = "CHAT_LOG_FILE"
ENV_MAX_CONVERSATION_HISTORY = "MAX_CONVERSATION_HISTORY"
ENV_CONTEXT_LIMIT_THRESHOLD = "CONTEXT_LIMIT_THRESHOLD"
ENV_MAX_RETRIES = "MAX_RETRIES"

# OpenAI limits
OPENAI_MAX_TOOLS = 128

# Defaults
DEFAULT_OPENAI_MODEL = "gpt-4o"
DEFAULT_ROUTER_MODEL = "gpt-5-mini"
DEFAULT_USER_TIMEZONE = "Europe/Berlin"
DEFAULT_MEMORY_FILE = "data/memory.json"
DEFAULT_CHAT_LOG_FILE = "data/chat.log"
DEFAULT_CHAT_LOG_DIR = "logs/chat"
ENV_CHAT_LOG_DIR = "CHAT_LOG_DIR"
LOG_TOOLS_SELECTED = "Tools for user=%s categories=%s: %s"
LOG_STICKY_CATEGORIES = "Sticky categories for user=%s: %s"
DEFAULT_MAX_CONVERSATION_HISTORY = 100
DEFAULT_CONTEXT_LIMIT_THRESHOLD = 0
DEFAULT_MAX_RETRIES = 3

# Bot config keys (used by BotConfigProvider)
BOT_CFG_JID = "jid"
BOT_CFG_PASSWORD = "password"
BOT_CFG_DEFAULT_RECEIVER = "default_receiver"
BOT_CFG_ALLOWED_JIDS = "allowed_jids"

# Bot type
BOT_TYPE_XMPP = "xmpp"

# Error messages
ERR_AGENT_FAILED = "Sorry, I encountered an error processing your message. Please try again."
ERR_ROUTER_FAILED = (
    "The router model failed to classify your message. "
    "Please check the Ollama setup."
)
ERR_PLUGIN_LOAD_FAILED = "Failed to load plugin: {name}"

# Chat commands (matched case-insensitive)
CMD_CLEAR = {"clear", "clear chat", "clear chat history"}
CMD_RESTART = {"restart", "restart chat"}
CMD_USAGE = {"usage"}

# Command responses
RESP_CHAT_CLEARED = "Chat history cleared."
RESP_RESTART_TRIGGERED = "Restarting... please wait a moment."
WARN_CONTEXT_LIMIT = (
    "\n\n---\n"
    "Note: This conversation has used {tokens} input tokens "
    "(limit: {limit}). Consider sending 'clear' to reset context."
)

# Restart / Shutdown
RESTART_FLAG_FILE = "restart.flag"
SHUTDOWN_FLAG_FILE = "shutdown.flag"
PID_LOCK_FILE = "bot.pid"

# PID lock log messages
LOG_PID_SHUTTING_DOWN_OLD = "Shutting down existing instance (PID %d)..."
LOG_PID_OLD_STOPPED = "Previous instance stopped"
LOG_PID_STALE = "Stale PID file found (PID %d no longer running), overwriting"
LOG_PID_LOCK_ACQUIRED = "PID lock acquired (PID %d)"
LOG_PID_LOCK_RELEASED = "PID lock released"
ERR_PID_SHUTDOWN_TIMEOUT = (
    "ERROR: Previous instance (PID {pid}) did not stop within {timeout}s. Kill it manually."
)

# Credential files (auto-generated tokens stored in data/)
CREDENTIAL_DIR = "data"
RTM_TOKEN_FILE = "rtm_token"
ENV_RTM_TOKEN = "RTM_TOKEN"

# Feedback
DEFAULT_FEEDBACK_DIR = "feedback"
ENV_FEEDBACK_DIR = "FEEDBACK_DIR"

# Synonyms
SYNONYM_PREFIX = "synonym:"

# Pending retries
DEFAULT_PENDING_RETRIES_SUBDIR = "pending_retries"
RETRY_STATUS_PENDING = "pending"
RETRY_STATUS_COMPLETED = "completed"

# File uploads
DEFAULT_UPLOAD_DIR = "data/uploads"
ENV_UPLOAD_DIR = "UPLOAD_DIR"
PLUGIN_DATA_FILE_HANDLERS = "file_handlers"

# Transcription prefix (convention used by transcribe plugin file handler)
TRANSCRIPTION_PREFIX = "Transcription: "

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
DEFAULT_LEGACY_USAGE_FILE = "data/usage.log"
USAGE_LOG_PREFIX = "usage"
USAGE_LOG_SUFFIX = ".jsonl"
CORE_PLUGIN_NAME = "core"
USAGE_SOURCE_BOT = "bot"
USAGE_SOURCE_TEST = "test"

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

# Startup greeting
ENV_STARTUP_GREETING_ENABLED = "STARTUP_GREETING_ENABLED"
ENV_STARTUP_GREETING_MESSAGE = "STARTUP_GREETING_MESSAGE"
DEFAULT_STARTUP_GREETING_MESSAGE = "Hi, how may I assist you today?"
LOG_STARTUP_GREETING_SENT = "Sent startup greeting to %s"

# Log messages
LOG_PLUGIN_LOADED = "Loaded plugin: {name}"
LOG_PLUGIN_FAILED = "Failed to load plugin: {name}"
LOG_APP_STARTING = "Starting Business Assistant v2"
LOG_APP_STOPPED = "Business Assistant v2 stopped"
LOG_APP_RESTARTING = "Restart requested via restart.flag — restarting..."
LOG_APP_SHUTDOWN_FLAG = "Shutdown requested via shutdown.flag — stopping..."
LOG_STALE_RESTART_FLAG = "Stale restart.flag found (created before app start) — ignoring"
LOG_STALE_SHUTDOWN_FLAG = "Stale shutdown.flag found (created before app start) — ignoring"
LOG_OLLAMA_HEALTH_OK = "Ollama health check passed: %s"
LOG_OLLAMA_HEALTH_FAILED = "Ollama health check FAILED — is Ollama running? URL: %s"
LOG_AGENT_ERROR = "Error running AI agent"
LOG_RESPONSE_DURATION = "Response for %s: %.2fs total (router=%.2fs, agent=%.2fs)"
LOG_FILE_DOWNLOADED = "Downloaded file: %s (%d bytes)"
LOG_FILE_DOWNLOAD_FAILED = "Failed to download file from %s"
LOG_CHAT_CLEARED = "Chat history cleared for user %s"
LOG_RESTART_REQUESTED = "Restart requested by user %s"

# Memory tool responses
RESP_MEMORY_NOT_FOUND = "No memory found for key '{key}'."
RESP_MEMORY_GET = "{key}: {value}"
RESP_MEMORY_SET = "Remembered: {key} = {value}"
RESP_MEMORY_DELETED = "Forgot: {key}"
RESP_MEMORY_EMPTY = "Memory is empty."
RESP_MEMORY_LIST_HEADER = "Stored memories:"

# Feedback tool responses
RESP_FEEDBACK_SAVED = "Feedback saved: {filename}"
RESP_RETRY_CREATED = " Pending retry created: {retry_id}"
RESP_NO_PENDING_RETRIES = "No pending retries found."
RESP_PENDING_RETRIES_HEADER = "Pending retries ({count}):"
RESP_RETRY_NOT_FOUND = "Retry not found: {retry_id}"
RESP_RETRY_READ_ERROR = "Error reading retry file: {retry_id}"
RESP_RETRY_ALREADY_COMPLETED = "Retry already completed: {retry_id}"
RESP_RETRY_COMPLETED = "Retry completed: {retry_id}"
LOG_FEEDBACK_WRITTEN = "Feedback written to %s"
LOG_RETRY_SAVED = "Pending retry saved: %s"
LOG_RETRY_COMPLETED = "Retry completed: %s"

# Synonym tool responses
RESP_SYNONYM_SAVED = "Synonym saved: '{synonym}' \u2192 '{target}'"
RESP_NO_SYNONYMS = "No synonyms defined."
RESP_SYNONYMS_HEADER = "Command synonyms:"
RESP_SYNONYM_DELETED = "Synonym deleted: '{synonym}'"
RESP_SYNONYM_NOT_FOUND = "No synonym found for '{synonym}'."

# Usage report responses
RESP_NO_USAGE_DATA = "No usage data found."
RESP_USAGE_REPORT_FAILED = "Failed to generate usage report."

# File handling responses
RESP_FILE_RECEIVED = (
    "[File received: {filename} ({mime_type}, {size} bytes) saved to {path}]"
)
RESP_FILE_PROCESSED = "[File processed by {plugin}: {summary}]"

# Health check
OLLAMA_HEALTH_RESPONSE = "Ollama is running"

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

Users can define command synonyms so that custom words trigger existing commands. \
When a user asks to save a word as a synonym for a command, use add_synonym. \
Use list_synonyms to show all defined synonyms, and delete_synonym to remove one.

When calling tools that require no parameters, pass an empty arguments object {{}}. \
Do not use {{"_":{{}}}} or any other wrapper.

Current memory contents:
{memory_contents}

{plugin_extras}"""

# Router system prompt (for category selection)
ROUTER_SYSTEM_PROMPT = """\
You are a message router. Given the user's message, select which tool categories \
are needed to handle it. Return ONLY a JSON array of category names.

Available categories:
{category_list}

Examples:
- "check my emails" -> ["email"]
- "start workflow inbox zero" -> ["project_management"]
- "schedule a meeting about the project" -> ["calendar", "project_management"]
- "hello" -> []

If the message is general conversation (greetings, questions about yourself), \
return an empty list [].
If unsure which categories are needed, include all potentially relevant ones."""

# Business Assistant v2

Plugin-based XMPP chatbot using PydanticAI for natural language understanding and bot-commander for XMPP messaging. Users send free-form text messages and the AI agent interprets intent, calling plugin-provided tools.

## Architecture

```
User (XMPP) --> bot-commander (XmppAdapter) --> AIMessageHandler.handle()
  --> ThreadPoolExecutor --> PydanticAI agent.run_sync()
    --> agent calls tools (email, memory, etc.)
  --> BotResponse(text) --> XMPP reply
```

## Setup

1. Copy `.env.example` to `.env` and configure your settings
2. Run `install.bat` to install dependencies and run tests

## Usage

```bash
start.bat
```

Send messages via XMPP to interact with the assistant.

## Plugins

Plugins are separate packages discovered via the `PLUGINS` environment variable (comma-separated Python module names).

### Adding a Plugin

1. Create a Python package with a top-level `register(registry)` function
2. The function receives a `PluginRegistry` and registers PydanticAI tools
3. Add the module name to `PLUGINS` in `.env`
4. Install the plugin package as an editable dependency

### Available Plugins

- **business-assistant-imap-plugin** (`business_assistant_imap`): IMAP/SMTP email operations
- **business-assistant-calendar-plugin** (`business_assistant_calendar`): Google Calendar operations

### Plugin Configuration

Only plugins listed in the `PLUGINS` environment variable are loaded. Set it in `.env` as a comma-separated list of Python module names:

```bash
# Both plugins
PLUGINS=business_assistant_imap,business_assistant_calendar

# IMAP only
PLUGINS=business_assistant_imap

# Calendar only
PLUGINS=business_assistant_calendar

# No plugins
PLUGINS=
```

Each plugin also requires its own environment variables to function. If the required variable is missing, the plugin skips registration gracefully.

| Plugin | Required env var | Additional env vars |
|--------|-----------------|-------------------|
| `business_assistant_imap` | `IMAP_SERVER` | `IMAP_USERNAME`, `IMAP_PASSWORD`, `SMTP_SERVER`, etc. |
| `business_assistant_calendar` | `GOOGLE_CALENDAR_CREDENTIALS_PATH` | `GOOGLE_CALENDAR_TOKEN_PATH`, `GOOGLE_CALENDAR_ID`, `GOOGLE_CALENDAR_TIMEZONE`, `GOOGLE_CALENDAR_FREE_CHECK_IDS` |

See `.env.example` for all available settings.

## Memory System

The built-in memory system stores user preferences as key-value pairs in a JSON file. Users can teach the assistant aliases and preferences through natural conversation:

- "Remember: when I say Markus I mean meiners@xida.de"
- "Forget Markus"
- "What do you remember?"

## Development

```bash
# Run tests
tools\tests.bat

# Update dependencies and run checks
update.bat
```

## Dependencies

- [PydanticAI](https://github.com/pydantic/pydantic-ai) - AI agent framework
- [bot-commander](../bot-commander) - XMPP/Telegram bot framework
- [python-dotenv](https://github.com/theskumar/python-dotenv) - Environment variable loading

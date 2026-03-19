# Business Assistant v2

Plugin-based XMPP chatbot using PydanticAI for natural language understanding and bot-commander for XMPP messaging. Users send free-form text messages and the AI agent interprets intent, calling plugin-provided tools.

## Architecture

```
User (XMPP)
  |
  v
bot-commander (XmppAdapter)
  |
  v
AIMessageHandler.handle()
  |
  +-- Built-in commands (clear, restart)
  +-- Plugin command handlers (short-circuit before AI)
  +-- Message modifiers (transform text before AI)
  |
  v
Category Router (gpt-5-mini)          <-- Call 1: select plugin categories
  |
  v
PydanticAI agent.run_sync()           <-- Call 2: process with selected tools
  (via agent.override(tools=...))
  |
  v
Response processors (transform response)
  |
  v
BotResponse --> XMPP reply
```

### Dynamic Tool Loading

OpenAI limits function tools to 128 per API call. Instead of sending all tools with every request, the bot uses a **two-phase approach**:

1. A lightweight router model (`ROUTER_MODEL`, default `gpt-5-mini`) reads the user's message and selects which plugin categories are needed
2. Only the selected categories' tools are loaded for the main model via `agent.override()`

This reduces per-request tool count from ~100 to ~15-40 depending on the message, while allowing unlimited total tools across all plugins.

See [docs/TOOL_LIMIT.md](docs/TOOL_LIMIT.md) for details.

## Setup

1. Copy `.env.example` to `.env` and configure your settings
2. Run `install.bat` to install dependencies and run tests

## Usage

```bash
start.bat
```

Send messages via XMPP to interact with the assistant.

## Plugins

Plugins are separate packages discovered via the `PLUGINS` environment variable (comma-separated Python module names). Each plugin registers tools, system prompt additions, and optional hooks with a central `PluginRegistry`.

See [docs/plugins/plugin-development-guide.md](docs/plugins/plugin-development-guide.md) for creating new plugins.

### Available Plugins

| Plugin | Module | Description |
|--------|--------|-------------|
| IMAP | `business_assistant_imap` | Email operations (read, send, reply, forward, search, tags) |
| Calendar | `business_assistant_calendar` | Google Calendar (events, scheduling, ICS import) |
| RTM | `business_assistant_rtm` | Remember The Milk task management |
| Obsidian | `business_assistant_obsidian` | Obsidian vault note management |
| Project Management | `business_assistant_pm` | Project orchestration (links email/tasks/notes/files) |
| Filesystem | `business_assistant_filesystem` | File operations (read, write, copy, move) |
| Workingtimes | `business_assistant_workingtimes` | Time tracking (log hours, manage entries) |
| Transcribe | `business_assistant_transcribe` | Audio transcription via Whisper |
| TTS | `business_assistant_tts` | Text-to-speech (uses hooks, no AI tools) |

### Plugin Configuration

Only plugins listed in `PLUGINS` are loaded. Set it in `.env` as a comma-separated list:

```bash
PLUGINS=business_assistant_imap,business_assistant_calendar,business_assistant_rtm
```

Each plugin requires its own environment variables. If the required variable is missing, the plugin skips registration gracefully. See `.env.example` for all available settings.

### Plugin Hooks

Plugins can register hooks that run without consuming AI tool slots:

- **Command handlers**: Intercept messages before the AI (short-circuit with a direct response)
- **Message modifiers**: Transform message text before the AI processes it
- **Response processors**: Transform responses after the AI produces them

See [docs/COMMAND_HANDLER.md](docs/COMMAND_HANDLER.md) for details.

## Memory System

The built-in memory system stores user preferences as key-value pairs in a JSON file. Users can teach the assistant aliases and preferences through natural conversation:

- "Remember: when I say Markus I mean meiners@xida.de"
- "Forget Markus"
- "What do you remember?"

## File Handling

Plugins can register file handlers for specific MIME types. When a user sends a file attachment via XMPP, the bot downloads it and routes it to the appropriate handler. See [docs/plugins/features/FILE_UPLOAD.md](docs/plugins/features/FILE_UPLOAD.md).

## Restart and Shutdown

The bot supports file-based lifecycle control:

- `touch restart.flag` — hot-reload plugins and agent (polled every 5s)
- `touch shutdown.flag` — clean shutdown without restart
- Ctrl+C / SIGTERM — clean exit

## Configuration

Key environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | (required*) | OpenAI API key (*not required when using only Ollama) |
| `OPENAI_MODEL` | `gpt-4o` | Main model for processing requests |
| `OPENAI_API_BASE_URL` | (empty) | Custom OpenAI-compatible API endpoint |
| `OLLAMA_BASE_URL` | (empty) | Ollama API base URL (e.g. `http://localhost:11434/v1`) |
| `ROUTER_MODEL` | `gpt-5-mini` | Lightweight model for category routing |
| `PLUGINS` | (empty) | Comma-separated plugin module names |
| `XMPP_JID` | (required) | Bot's XMPP JID |
| `XMPP_PASSWORD` | (required) | Bot's XMPP password |
| `XMPP_DEFAULT_RECEIVER` | (required) | Default recipient JID |
| `MEMORY_FILE` | `data/memory.json` | Path to memory store |
| `USER_TIMEZONE` | `Europe/Berlin` | IANA timezone for time display |

See `.env.example` for the complete list.

### LLM Providers

The bot supports three provider options for both the main agent and router:

- **OpenAI** (default) — set `OPENAI_API_KEY`
- **OpenAI-compatible APIs** (e.g. DeepSeek) — set `OPENAI_API_BASE_URL` / `ROUTER_API_BASE_URL`
- **Ollama** (local models) — set `OLLAMA_BASE_URL` (e.g. `http://localhost:11434/v1`), no API key needed

See [docs/LLM_MODELS_configuration.md](docs/LLM_MODELS_configuration.md) for detailed configuration examples and provider priority.

## Development

```bash
# Install dependencies
uv sync --all-extras

# Run unit tests
uv run pytest tests/ -v --ignore=tests/integration

# Run integration tests (requires OPENAI_API_KEY)
uv run pytest tests/integration/ -v

# Lint
uv run ruff check src/ tests/

# Type check
uv run mypy src/
```

## Dependencies

- [PydanticAI](https://github.com/pydantic/pydantic-ai) - AI agent framework
- [bot-commander](../bot-commander) - XMPP/Telegram bot framework
- [python-dotenv](https://github.com/theskumar/python-dotenv) - Environment variable loading

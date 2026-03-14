# Business Assistant v2 - Development Guide

## Project Overview

Plugin-based XMPP chatbot using PydanticAI + bot-commander. Source code in `src/business_assistant/`.

## Commands

- `uv sync --all-extras` — Install dependencies
- `uv run pytest tests/ -v` — Run all tests
- `uv run pytest tests/ -v --ignore=tests/integration` — Run unit tests
- `uv run pytest tests/integration/ -v` — Run integration tests (requires OPENAI_API_KEY)
- `uv run ruff check src/ tests/` — Lint
- `uv run mypy src/` — Type check
- `uv run python -m business_assistant.main` — Start the app

## Architecture

- `config/` — Settings (frozen dataclasses) + constants
- `memory/` — JSON-backed key-value store (thread-safe)
- `plugins/` — Plugin registry + dynamic loader
- `agent/` — PydanticAI agent setup, deps, system prompt
- `bot/` — bot-commander integration (handler, config provider, app lifecycle)

## Key Protocols

- `MessageHandler` (bot-commander): `handle(BotMessage) -> BotResponse`
- `BotConfigProvider` (bot-commander): `get_bot_setting(key, fallback) -> str`
- Plugin entry point: `register(registry: PluginRegistry) -> None`

## Restarting the Bot

The bot supports file-based restart. After making code changes to plugins or the bot itself, always trigger a restart by creating the sentinel file:

```bash
touch restart.flag
```

The bot polls for `restart.flag` every 5 seconds. When detected, it:
1. Deletes the file
2. Shuts down the current application (XMPP disconnect, plugin cleanup)
3. Starts a fresh application with reloaded plugins, settings, and agent

SIGINT (Ctrl+C) or SIGTERM cause a clean exit without restart.

**Important:** `restart.flag` only reloads code changes in already-loaded plugins. When activating a new plugin (adding to `PLUGINS` in `.env` or installing a new plugin package), you must fully stop and restart the bot process (Ctrl+C, then `uv run python -m business_assistant.main`).

## Shutting Down the Bot

The bot also supports file-based shutdown via `shutdown.flag`. This causes a clean exit (no restart):

```bash
touch shutdown.flag
```

The bot polls for `shutdown.flag` every 5 seconds (checked before `restart.flag`). When detected, it deletes the file and stops the process.

## Testing After Changes

**Important:** The bot must be stopped before running tests. The bot process locks shared dependencies and will cause `uv run` to hang.

Before testing, shut down the bot:
```bash
touch shutdown.flag
```

Wait a few seconds for the bot to stop, then run tests in this order:

1. **Unit tests** (both repos):
   - `cd business-assistant-imap-plugin && uv run pytest tests/ -v`
   - `cd business-assistant-v2 && uv run pytest tests/ -v --ignore=tests/integration`

2. **Lint** (both repos):
   - `uv run ruff check src/ tests/`

3. **Integration tests** (require OPENAI_API_KEY in .env):
   - `uv run pytest tests/integration/ -v`
   - These test AI decision-making with real OpenAI API + mocked services
   - If an integration test fails, the system prompt likely needs adjustment

4. **Code analysis** (runs on v2 + all plugins):
   - `powershell -Command "cd 'D:\GIT\BenjaminKobjolke\business-assistant-v2'; cmd /c '.\tools\analyze_code.bat'"`
   - After the analysis completes, check each project's `code_analysis_results/` folder:
     - `D:\GIT\BenjaminKobjolke\business-assistant-v2\code_analysis_results\`
     - `D:\GIT\BenjaminKobjolke\business-assistant-imap-plugin\code_analysis_results\`
     - `D:\GIT\BenjaminKobjolke\business-assistant-calendar-plugin\code_analysis_results\`
     - `D:\GIT\BenjaminKobjolke\business-assistant-rtm-plugin\code_analysis_results\`

Fix any reported issues before committing.

After testing, restart the bot:
```bash
powershell -Command "Start-Process 'D:\GIT\BenjaminKobjolke\business-assistant-v2\start_after_tests.bat'"
```

## Git Commands

Never use compound commands (`cd /path && git ...`) with git. Run all git commands directly without `cd` prefixes. If you need to operate on a different repo, use separate commands.

## XMPP Event Loop Constraint

`handle()` in `bot/handler.py` is called from the XMPP async event loop. **Never call `run_sync()` or any other blocking async operation directly inside `handle()`.** This includes PydanticAI agent calls, HTTP requests, or any code that creates/runs an event loop.

All such calls must go through `self._executor.submit()` (ThreadPoolExecutor) to run in a separate thread. The main agent call and the category router call both run inside `_run_agent()` for this reason.

Symptom if violated: `RuntimeError: This event loop is already running`.

## Rules

### Common Rules

- Use objects for related values (DTOs/Settings/Config)
- Centralize string constants in `config/constants.py`
- Tests are mandatory — use pytest
- Use `spec=` with MagicMock
- DRY — no code duplication

### Python Rules

- `pyproject.toml` is the single source of truth
- Enforce formatting + linting + type checking (ruff + mypy)
- Type hints on all public APIs
- Centralized configuration with environment-driven settings
- Tests must be fast and isolated (no network)
- Use `frozen=True` dataclasses for settings

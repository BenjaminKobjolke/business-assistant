# Business Assistant v2 - Development Guide

## Project Overview

Plugin-based XMPP chatbot using PydanticAI + bot-commander. Source code in `src/business_assistant/`.

## Commands

- `uv sync --all-extras` — Install dependencies
- `uv run pytest tests/ -v` — Run tests
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

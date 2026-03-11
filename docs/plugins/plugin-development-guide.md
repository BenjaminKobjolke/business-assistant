# Plugin Development Guide

## Overview

Business Assistant v2 uses a plugin system to extend functionality. Each plugin is a separate Python package that registers tools, system prompt additions, and optional file handlers with a central `PluginRegistry`.

Plugins are loaded at startup from the `PLUGINS` environment variable (comma-separated module names).

## Project Setup

Create a separate repository with this structure:

```
business-assistant-my-plugin/
├── src/
│   └── business_assistant_my/
│       ├── __init__.py
│       ├── constants.py
│       ├── plugin.py        # Entry point
│       └── service.py       # Business logic
├── tests/
│   └── test_plugin.py
└── pyproject.toml
```

### pyproject.toml

```toml
[project]
name = "business-assistant-my-plugin"
version = "0.1.0"
description = "My plugin for Business Assistant v2"
requires-python = ">=3.11,<3.13"
dependencies = [
    "business-assistant-v2",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/business_assistant_my"]

[tool.uv.sources]
business-assistant-v2 = { path = "../business-assistant-v2", editable = true }
```

## Entry Point

Every plugin must expose a `register(registry: PluginRegistry) -> None` function at the module level (typically in `plugin.py` with `__init__.py` re-exporting it):

```python
from business_assistant.plugins.registry import PluginInfo, PluginRegistry

def register(registry: PluginRegistry) -> None:
    settings = _load_settings()
    if settings is None:
        logger.info("Plugin not configured, skipping")
        return

    info = PluginInfo(
        name="my_plugin",
        description="Does useful things",
        system_prompt_extra=SYSTEM_PROMPT,
        category="my_category",
    )
    tools = [Tool(_my_tool, name="my_tool")]
    registry.register(info, tools)
```

### Conditional Registration

Plugins that require authentication can register in two phases:

1. **Setup mode** — register only auth tools when credentials are missing
2. **Full mode** — register all tools when credentials are present

See the RTM plugin (`business_assistant_rtm/plugin.py`) for a complete example.

## PluginInfo

```python
@dataclass
class PluginInfo:
    name: str                                   # Unique plugin name
    description: str                            # Human-readable description
    system_prompt_extra: str = ""              # Appended to the AI system prompt
    category: str = ""                         # Feature category (e.g. "todo", "email")
    required_categories: tuple[str, ...] = ()  # Categories this plugin depends on
```

## Creating Tools

Tools use `pydantic_ai.Tool` with a function that receives `RunContext[Deps]`:

```python
from pydantic_ai import RunContext, Tool
from business_assistant.agent.deps import Deps

def _list_items(ctx: RunContext[Deps], query: str = "") -> str:
    """List items, optionally filtered by query."""
    service = ctx.deps.plugin_data[PLUGIN_DATA_SERVICE]
    return service.list_items(query)

tools = [Tool(_list_items, name="list_items")]
```

- The function docstring becomes the tool description for the AI
- All parameters except `ctx` are exposed to the AI agent
- Return type must be `str`
- Tool names must be unique across all plugins

## Plugin Categories

Categories declare what feature area a plugin provides. Only one plugin per category is allowed:

```python
# constants.py
PLUGIN_CATEGORY = "todo"

# plugin.py
info = PluginInfo(
    name="rtm",
    description="Task management",
    category=PLUGIN_CATEGORY,
)
```

Standard categories defined in `config/constants.py`:
- `CATEGORY_TODO = "todo"`
- `CATEGORY_EMAIL = "email"`
- `CATEGORY_CALENDAR = "calendar"`

Use `required_categories` to declare dependencies on other plugins:

```python
info = PluginInfo(
    name="meeting_scheduler",
    category="meetings",
    required_categories=("calendar", "email"),
)
```

Unmet requirements are logged as warnings at startup.

## Plugin Data

Share state between registration and tool execution via `registry.plugin_data`:

```python
# During registration:
registry.plugin_data[PLUGIN_DATA_SERVICE] = MyService(settings)

# During tool execution:
def _my_tool(ctx: RunContext[Deps]) -> str:
    service = ctx.deps.plugin_data[PLUGIN_DATA_SERVICE]
    return service.do_work()
```

Use constants for all plugin data keys to avoid collisions.

## File Handlers

Register handlers for specific MIME types to process file uploads:

```python
from business_assistant.files.downloader import DownloadedFile
from business_assistant.files.handler_registry import FileHandlerResult

def handle_audio(downloaded: DownloadedFile, user_id: str) -> FileHandlerResult:
    transcript = transcribe(downloaded.path)
    return FileHandlerResult(summary=f'Transcription: "{transcript}"')

def register(registry: PluginRegistry) -> None:
    registry.register_file_handler(
        mime_patterns=["audio/*"],
        plugin_name="my_plugin",
        handler=handle_audio,
    )
```

See [FILE_UPLOAD.md](features/FILE_UPLOAD.md) for details.

## Configuration

Use frozen dataclasses for settings, loaded from environment variables:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class MySettings:
    api_key: str
    endpoint: str = "https://api.example.com"

def _load_settings() -> MySettings | None:
    api_key = os.getenv(ENV_API_KEY, "")
    if not api_key:
        return None
    return MySettings(api_key=api_key)
```

## Logging

Set up per-plugin logging with a dedicated log file:

```python
from business_assistant.config.log_setup import add_plugin_logging

def register(registry: PluginRegistry) -> None:
    add_plugin_logging("my_plugin", "business_assistant_my")
```

This creates `logs/my_plugin/my_plugin.log`. See [LOGGING.md](features/LOGGING.md) for details.

## Testing

Use pytest with mocked registry and `spec=` on all MagicMock instances:

```python
from unittest.mock import MagicMock
from business_assistant.plugins.registry import PluginRegistry

class TestPluginRegistration:
    def test_register_with_config(self, monkeypatch) -> None:
        monkeypatch.setenv("MY_API_KEY", "test-key")
        registry = PluginRegistry()
        register(registry)
        assert len(registry.plugins) == 1
        assert registry.plugins[0].name == "my_plugin"
```

Tests must be fast and isolated — no network calls.

## Constants

Centralize all strings in `constants.py`:

```python
# Environment variable names
ENV_API_KEY = "MY_API_KEY"

# Plugin metadata
PLUGIN_NAME = "my_plugin"
PLUGIN_CATEGORY = "my_category"
PLUGIN_DESCRIPTION = "My plugin description"

# Plugin data keys
PLUGIN_DATA_SERVICE = "my_service"

# System prompt
SYSTEM_PROMPT = """You have access to my_plugin tools: ..."""
```

## Activation

Add the plugin module name to `PLUGINS` in `.env`:

```
PLUGINS=business_assistant_rtm,business_assistant_imap,business_assistant_my
```

After adding a new plugin, fully restart the bot process (Ctrl+C, then `uv run python -m business_assistant.main`). The `restart.flag` mechanism only reloads existing plugins.

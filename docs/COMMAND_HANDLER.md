# Command Handler & Message Modifier Hooks

Plugins can register **command handlers** and **message modifiers** to intercept or transform messages without consuming AI tool slots (OpenAI limits tools to 128).

## Command Handlers

Command handlers intercept messages **before** the AI agent sees them. If a handler returns a `BotResponse`, it is sent directly to the user and the AI is never called.

### Registration

```python
from bot_commander.types import BotResponse

def my_command_handler(text: str, user_id: str, plugin_data: dict) -> BotResponse | None:
    if text.lower().strip() == "my command":
        return BotResponse(text="Handled directly!")
    return None  # Not our command, let AI handle it

def register(registry: PluginRegistry) -> None:
    registry.register_command_handler(my_command_handler)
```

### Signature

```python
(text: str, user_id: str, plugin_data: dict) -> BotResponse | None
```

- `text` — raw message text from the user
- `user_id` — sender's user ID
- `plugin_data` — shared plugin state dict
- Return `BotResponse` to short-circuit, `None` to continue to the next handler or AI

### Execution Order

1. Built-in commands (`clear`, `restart`)
2. Plugin command handlers (in registration order)
3. AI agent (only if no handler returned a response)

## Message Modifiers

Message modifiers transform the message text **before** the AI processes it. They always run (they cannot short-circuit). Use them to inject context the AI needs.

### Registration

```python
def my_message_modifier(text: str, user_id: str, plugin_data: dict) -> str:
    if some_condition(user_id):
        return "[Extra context for AI]\n" + text
    return text

def register(registry: PluginRegistry) -> None:
    registry.register_message_modifier(my_message_modifier)
```

### Signature

```python
(text: str, user_id: str, plugin_data: dict) -> str
```

- Must return the (possibly modified) text string
- Modifiers are chained: each receives the output of the previous one

## Architecture

```
User message
    |
    v
Built-in commands (clear, restart)
    |  (not matched)
    v
Plugin command handlers  -->  BotResponse (short-circuit)
    |  (all returned None)
    v
Message modifiers (transform text)
    |
    v
AI agent processes modified text
    |
    v
Response processors (transform response)
    |
    v
Bot adapter sends response
```

## Key Files

- `src/business_assistant/config/constants.py` — `PLUGIN_DATA_COMMAND_HANDLERS`, `PLUGIN_DATA_MESSAGE_MODIFIERS`
- `src/business_assistant/plugins/registry.py` — `register_command_handler()`, `register_message_modifier()`
- `src/business_assistant/bot/handler.py` — execution in `_handle_command()` and `handle()`

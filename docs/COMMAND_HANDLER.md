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

1. Built-in commands (`clear`, `restart`) — checked against typed text
2. Plugin command handlers (in registration order) — checked against typed text
3. **Voice command check** — if the message has no typed text and an audio attachment was transcribed (summary starting with `Transcription: `), the transcription is checked against steps 1-2
4. AI agent (only if no handler returned a response)

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
Process attachments (download + file handlers)
    |
    v
Voice command check (voice-only messages)
    |  transcription matched a command?  -->  BotResponse (short-circuit)
    |  (no match or typed text present)
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

## Synonyms

Users can define custom command synonyms that map to existing commands. This is especially useful for voice input where spoken words (e.g. "löschen") need to trigger built-in commands (e.g. "clear").

Synonyms are stored in the `MemoryStore` with a `synonym:` key prefix. When a message arrives, the handler checks if the normalized text matches a stored synonym and resolves it to the target command before any other command matching.

### Management

Synonyms are managed conversationally via three AI tools:

- **add_synonym** — define a new synonym (e.g. "löschen" → "clear")
- **list_synonyms** — show all defined synonyms
- **delete_synonym** — remove a synonym

### Resolution

1. Incoming text is normalized (lowercased, trimmed)
2. A memory lookup checks for `synonym:{normalized}`
3. If found, the text is replaced with the target value
4. Normal command matching proceeds (built-in → plugin → AI)

Resolution is single-level only — synonyms cannot chain to other synonyms.

## Key Files

- `src/business_assistant/config/constants.py` — `PLUGIN_DATA_COMMAND_HANDLERS`, `PLUGIN_DATA_MESSAGE_MODIFIERS`
- `src/business_assistant/plugins/registry.py` — `register_command_handler()`, `register_message_modifier()`
- `src/business_assistant/bot/handler.py` — execution in `_handle_command()` and `handle()`

# File Upload Support

The bot detects file attachments sent via XMPP (using HTTP File Upload / XEP-0363), downloads them locally, and informs the AI agent. Plugins can register handlers for specific MIME types to process files automatically (e.g. transcribe audio, parse images).

## Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `UPLOAD_DIR` | No | `data/uploads` | Local directory for downloaded files |

The upload directory is created automatically on startup.

## How it works

### 1. Attachment detection (bot-commander)

When an XMPP client sends a file, it uploads the file to the server's HTTP upload service and sends a message containing:
- The file URL in the message body
- An OOB XML element (`jabber:x:oob` namespace) with the URL

The `XmppAdapter` parses the stanza XML for OOB elements and creates `Attachment` objects (url, filename, mime_type). These are passed to `BotMessage.attachments`.

### 2. File download (business-assistant-v2)

In `AIMessageHandler.handle()`, before calling the AI agent, `_process_attachments()` runs:

1. For each attachment, `FileDownloader.download()` fetches the URL to the upload directory
2. Files are saved with unique names: `{YYYYMMDD}_{uuid8}_{sanitized_filename}`
3. A context prefix is prepended to the agent text:
   ```
   [File received: voice.ogg (audio/ogg, 45320 bytes) saved to data/uploads/20260310_a1b2c3d4_voice.ogg]
   ```

### 3. Plugin file handlers (optional)

If any plugins registered file handlers, matching handlers run on the downloaded file. Their results are appended to the context:
```
[File processed by audio-plugin: Transcription: "Hello world"]
```

The AI agent receives the full context (file info + handler results + original message text) and can respond accordingly.

## Writing a plugin file handler

Plugins can register handlers for MIME types using `PluginRegistry.register_file_handler()`:

```python
from business_assistant.files.downloader import DownloadedFile
from business_assistant.files.handler_registry import FileHandlerResult


def handle_audio(downloaded: DownloadedFile, user_id: str) -> FileHandlerResult:
    """Process an audio file (e.g. transcribe it)."""
    transcript = my_transcription_service(downloaded.path)
    return FileHandlerResult(summary=f'Transcription: "{transcript}"')


def register(registry: PluginRegistry) -> None:
    registry.register_file_handler(
        mime_patterns=["audio/*"],
        plugin_name="audio-transcriber",
        handler=handle_audio,
    )
```

### MIME pattern matching

- Exact match: `"audio/ogg"` matches only `audio/ogg`
- Wildcard: `"audio/*"` matches `audio/ogg`, `audio/mpeg`, etc.
- Multiple patterns: `["image/png", "image/jpeg"]`
- Multiple handlers can match the same file; all are executed

### FileHandlerResult

| Field | Type | Default | Description |
|---|---|---|---|
| `summary` | `str` | — | Human-readable result (shown to AI agent) |
| `processed` | `bool` | `True` | Whether the file was successfully processed |

### DownloadedFile

| Field | Type | Description |
|---|---|---|
| `path` | `str` | Full path to the downloaded file |
| `filename` | `str` | Original filename |
| `mime_type` | `str` | MIME type (e.g. `audio/ogg`) |
| `size` | `int` | File size in bytes |

## Architecture

```
XMPP Client
    ↓ (HTTP File Upload + OOB)
XmppAdapter._extract_attachments()
    ↓ (Attachment objects)
BotMessage(attachments=(...))
    ↓
AIMessageHandler._process_attachments()
    ├── FileDownloader.download()     → saves to data/uploads/
    └── FileHandlerRegistry.get_handlers() → runs matching plugin handlers
    ↓ (context prefix + original text)
PydanticAI Agent
```

Key files:

- `src/bot_commander/types.py` — `Attachment` dataclass
- `src/bot_commander/adapters/xmpp.py` — `_extract_attachments()` OOB parser
- `src/business_assistant/files/downloader.py` — `FileDownloader`, `DownloadedFile`
- `src/business_assistant/files/handler_registry.py` — `FileHandlerRegistry`, `FileHandlerResult`
- `src/business_assistant/plugins/registry.py` — `register_file_handler()` convenience
- `src/business_assistant/bot/handler.py` — `_process_attachments()` integration
- `src/business_assistant/bot/app.py` — wiring `FileDownloader` on startup
- `src/business_assistant/config/constants.py` — upload-related constants
- `src/business_assistant/config/settings.py` — `upload_dir` in `AppSettings`

## Supported XMPP clients

Any client that implements XEP-0363 (HTTP File Upload) with XEP-0066 (OOB) will work:
- Conversations (Android)
- Gajim (Desktop)
- Dino (Desktop)
- Monal (iOS/macOS)

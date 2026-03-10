# FTP Upload Service

The bot provides a core FTP upload service that plugins can use to upload files and get public URLs. The email plugin uses it to upload inline images and attachments so the AI can share them in chat.

## Configuration

Set these environment variables in `.env` (see `.env.example`):

| Variable | Required | Default | Description |
|---|---|---|---|
| `FTP_HOST` | Yes | — | FTP server hostname |
| `FTP_USERNAME` | Yes | — | FTP login username |
| `FTP_PASSWORD` | Yes | — | FTP login password |
| `FTP_PORT` | No | `21` | FTP server port |
| `FTP_USE_TLS` | No | `true` | Use FTPS (TLS) connection |
| `FTP_BASE_PATH` | Yes | — | Remote directory for uploads (e.g. `/`) |
| `FTP_BASE_URL` | Yes | — | Public URL prefix (e.g. `https://example.com/files`) |

If `FTP_HOST` is not set, the service is not created and plugins work without it.

## How it works

On startup, if FTP is configured, the bot creates an `FtpUploadService` and stores it in `plugin_data["ftp_upload"]`. Any plugin can retrieve it:

```python
ftp_service = ctx.deps.plugin_data.get("ftp_upload")
if ftp_service:
    url = ftp_service.upload(file_bytes, "filename.png")
    # url = "https://example.com/files/a1b2c3d4_filename.png"
```

Each upload generates a unique filename (`{8-char-uuid}_{original_name}`) to avoid collisions.

## Email plugin integration

Uploads happen **on-demand** via the `get_attachment_url` tool, not automatically when viewing an email.

### Workflow

1. `show_email` returns attachment metadata (filename, content_type, size, content_id, is_inline) — no FTP upload
2. When the user asks to see/download a specific attachment, the AI calls `get_attachment_url(email_id, filename)`
3. The tool uploads the file via FTP and returns a shareable URL

### Attachment metadata from `show_email`

| Field | Description |
|---|---|
| `filename` | Original filename |
| `content_type` | MIME type (e.g. `image/png`) |
| `size` | Size in bytes |
| `content_id` | CID reference (inline attachments only) |
| `is_inline` | `true` for inline attachments |

### `get_attachment_url` response

Returns JSON: `{"filename": "...", "url": "https://...", "content_type": "..."}`

If FTP is not configured, returns an error message. FTP upload failures are handled gracefully with descriptive error messages.

## Architecture

```
AppSettings.ftp (FtpSettings)
    ↓
bot/app.py → FtpUploadService → plugin_data["ftp_upload"]
    ↓
plugins access via ctx.deps.plugin_data.get("ftp_upload")
```

Key files:

- `src/business_assistant/config/constants.py` — FTP env var names and defaults
- `src/business_assistant/config/settings.py` — `FtpSettings` dataclass
- `src/business_assistant/upload/ftp_service.py` — `FtpUploadService` class
- `src/business_assistant/bot/app.py` — wiring into `plugin_data`

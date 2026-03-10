# Plugin Logging

The bot provides centralized rotating log files. Each plugin gets its own log directory and file, separate from the main bot logs.

## File layout

```
logs/
  app/app.log              # main bot (business_assistant.*)
  imap/imap.log            # IMAP plugin (business_assistant_imap.*)
  calendar/calendar.log    # calendar plugin (business_assistant_calendar.*)
```

Log files rotate automatically (default: 5 MB, 3 backups).

## Enabling plugin logging

Call `add_plugin_logging()` at the start of your `register()` function:

```python
from business_assistant.config.log_setup import add_plugin_logging

def register(registry: PluginRegistry) -> None:
    add_plugin_logging("myplugin", "my_plugin_namespace")
    # ... rest of registration
```

**Parameters:**

| Parameter | Description | Example |
|---|---|---|
| `plugin_name` | Directory and file name under `logs/` | `"imap"` |
| `logger_namespace` | Python logger namespace (top-level package) | `"business_assistant_imap"` |

This creates `logs/myplugin/myplugin.log` and attaches a `RotatingFileHandler` to the `my_plugin_namespace` logger. All child loggers (e.g. `my_plugin_namespace.email_service`) inherit the handler automatically.

## Using the logger

Use standard Python logging in any module within your plugin:

```python
import logging

logger = logging.getLogger(__name__)

def some_function():
    logger.info("Processing started")
    logger.debug("Detail: value=%s", value)
    logger.warning("Something unexpected: %s", detail)
```

As long as `__name__` falls under the registered namespace, log output goes to both:
- The **console** (via root logger inheritance)
- Your plugin's **log file** (via the namespace handler)

No duplicate output occurs.

## Configuration

All settings are controlled via environment variables (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Root log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `LOG_DIR` | `logs` | Base directory for all log files |
| `LOG_MAX_BYTES` | `5242880` (5 MB) | Max size per log file before rotation |
| `LOG_BACKUP_COUNT` | `3` | Number of rotated backup files to keep |

## Restart safety

`add_plugin_logging()` is idempotent. On bot restart (via `restart.flag`), calling it again does not create duplicate handlers.

## Log format

All log entries use the format:

```
2026-03-10 14:23:01,234 [INFO] business_assistant_imap.email_service: search_emails: query='linux', folder='INBOX', limit=20
```

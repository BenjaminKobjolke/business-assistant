# `usage` Command

Displays an AI token usage and cost report directly in chat, without invoking the AI agent.

## Trigger

Type `usage` (case-insensitive) in the chat.

## Output

A text report showing token consumption and estimated costs across 8 time periods:

- Today / Yesterday
- This Week / Last Week
- This Month / Last Month
- This Year / Last Year

Each period shows total requests, input/output/cache tokens, and cost. When multiple models were used in a period, a per-model breakdown is included.

### Example

```
Usage Report (Europe/Berlin)

Today: 12 req, $0.0142
  in 45.2k | out 3.1k | cache 38.0k

Yesterday: 8 req, $0.0098
  in 30.5k | out 2.0k | cache 25.1k
  - gpt-4o: 6 req, $0.0091
  - gpt-5-mini: 2 req, $0.0007

This Week: 42 req, $0.0480
  in 150.3k | out 10.2k | cache 120.0k
  ...
```

## How It Works

1. Registered as a command handler during app startup (`bot/app.py`)
2. Reads JSONL usage logs from the configured `USAGE_LOG_DIR` (default: `logs/app/usage/`)
3. Loads model pricing from a local SQLite cache (`data/price_cache.db`), auto-refreshed from litellm every 24 hours
4. Aggregates stats per time period and formats the report

## Configuration

| Setting | Env Var | Default | Description |
|---------|---------|---------|-------------|
| Log directory | `USAGE_LOG_DIR` | `logs/app/usage` | Where usage JSONL files are stored |
| Timezone | `USER_TIMEZONE` | `Europe/Berlin` | Timezone for period boundaries |

## Key Files

- `src/business_assistant/usage/command.py` — command handler factory
- `src/business_assistant/usage/formatter.py` — report text formatting
- `src/business_assistant/usage/reader.py` — JSONL log file reader
- `src/business_assistant/usage/aggregator.py` — time period definitions and stats aggregation
- `src/business_assistant/usage/prices.py` — model pricing cache (litellm)
- `src/business_assistant/config/constants.py` — `CMD_USAGE`

## CLI Equivalent

The same logic powers the standalone CLI tool:

```bash
uv run python -m tools.log_analyze
```

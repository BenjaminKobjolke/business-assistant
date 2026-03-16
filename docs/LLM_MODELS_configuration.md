# LLM Model Configuration

The business assistant makes two separate AI API calls per user message:

1. **Router call** — a lightweight model that selects which plugin categories (email, calendar, etc.) are needed for the message.
2. **Main agent call** — the full model that processes the message with the selected tools.

Both calls use OpenAI-compatible APIs. The router can optionally use a different API provider (e.g. DeepSeek) to reduce costs.

## Environment Variables

### Main Agent

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | Yes | — | API key for the main agent |
| `OPENAI_MODEL` | No | `gpt-4o` | Model name for the main agent |

The main agent always uses the standard OpenAI API endpoint.

### Router

| Variable | Required | Default | Description |
|---|---|---|---|
| `ROUTER_MODEL` | No | `gpt-5-mini` | Model name for the router |
| `ROUTER_API_KEY` | No | — | API key for the router API (falls back to `OPENAI_API_KEY`) |
| `ROUTER_API_BASE_URL` | No | — | Base URL for the router API (if empty, uses OpenAI) |

When `ROUTER_API_BASE_URL` is set, the router uses that endpoint with `ROUTER_API_KEY` (or `OPENAI_API_KEY` as fallback). When not set, the router uses the standard OpenAI API.

## Example Configurations

### OpenAI Only (default)

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
```

Both router and main agent use OpenAI. The router defaults to `gpt-5-mini`.

### DeepSeek Router + OpenAI Main Agent

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
ROUTER_MODEL=deepseek-chat
ROUTER_API_KEY=sk-...
ROUTER_API_BASE_URL=https://api.deepseek.com
```

The router uses DeepSeek for cheap category selection. The main agent uses OpenAI for tool execution.

### Custom Router Model on OpenAI

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
ROUTER_MODEL=gpt-4o-mini
```

Both use OpenAI, but the router uses a cheaper model. No `ROUTER_API_BASE_URL` needed.

## API Compatibility Requirements

- **Router API**: Must support structured output (JSON response with a `categories` list). Most OpenAI-compatible APIs support this.
- **Main agent API**: Must support tool/function calling. This is the standard OpenAI API.

## Architecture

```
User Message
    |
    v
[Router Call] -----> ROUTER_API_BASE_URL (or OpenAI)
    |                 Model: ROUTER_MODEL
    |                 Returns: list of category names
    v
[Tool Selection] --- Filters tools to selected categories
    |
    v
[Main Agent Call] -> OpenAI API
    |                 Model: OPENAI_MODEL
    |                 Tools: selected category tools + core tools
    v
Response
```

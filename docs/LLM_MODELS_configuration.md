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
| `OPENAI_API_BASE_URL` | No | — | Base URL for the main agent API (if empty, uses OpenAI) |

When `OPENAI_API_BASE_URL` is set, the main agent uses that endpoint with `OPENAI_API_KEY`. When not set, the main agent uses the standard OpenAI API.

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

### DeepSeek for Both Calls

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=deepseek-chat
OPENAI_API_BASE_URL=https://api.deepseek.com
ROUTER_MODEL=deepseek-chat
ROUTER_API_KEY=sk-...
ROUTER_API_BASE_URL=https://api.deepseek.com
```

Both router and main agent use DeepSeek.

### Custom Router Model on OpenAI

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
ROUTER_MODEL=gpt-4o-mini
```

Both use OpenAI, but the router uses a cheaper model. No `ROUTER_API_BASE_URL` needed.

## Performance Notes

### Avoid Reasoning Models for the Main Agent

Reasoning models (e.g. `deepseek-reasoner`/R1, `o1`, `o3`) perform internal chain-of-thought before responding, adding significant latency. For a tool-calling chatbot, standard chat models are faster and equally capable.

**Benchmark** (same query, DeepSeek API, 2026-03-18):

| Main Agent Model | Total | Router | Agent | Per LLM request |
|---|---|---|---|---|
| `deepseek-reasoner` (R1) | 25.16s | 4.66s | 20.5s | ~7.4s |
| `deepseek-chat` (V3) | 14.2s | 3.09s | 11.11s | ~5.6s |

Switching from `deepseek-reasoner` to `deepseek-chat` reduced total response time by 44%.

### Measuring Performance

Chat logs include timing and tool call data per message:

- `duration_s` — total response time
- `router_duration_s` / `agent_duration_s` — breakdown by phase
- `tools_called` / `tool_call_count` / `llm_requests` — tool usage details

Logs are at `logs/chat/<user>/<timestamp>.jsonl`.

### Comparing Models

Use [Artificial Analysis](https://artificialanalysis.ai/) to compare speed (tokens/sec), latency (TTFT), quality, and pricing across providers and models.

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
[Main Agent Call] -> OPENAI_API_BASE_URL (or OpenAI)
    |                 Model: OPENAI_MODEL
    |                 Tools: selected category tools + core tools
    v
Response
```

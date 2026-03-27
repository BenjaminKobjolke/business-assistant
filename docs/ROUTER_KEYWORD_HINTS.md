# Router Keyword Hints

## Overview

The category router uses a lightweight AI model (e.g., Qwen 2.5:7b) to classify user messages into plugin categories. Small models sometimes misclassify queries — for example, routing "Do I have unread emails?" to the `web` category instead of `email`.

**Keyword hints** supplement the AI router with deterministic keyword-based category detection. When the user's message contains a known keyword, the corresponding category is automatically added to the AI-selected categories.

## How It Works

1. The AI router classifies the message and returns a set of categories
2. The message text is tokenized into words
3. Each word is checked against `ROUTER_KEYWORD_HINTS` (case-insensitive)
4. Matching categories are merged with the AI result
5. The combined set is used to select plugin tools

Keyword hints only **add** categories — they never remove categories selected by the AI. This ensures the AI model's correct classifications are preserved while preventing common misroutes.

## Current Keyword Mappings

| Keyword | Category |
|---------|----------|
| `email`, `emails`, `e-mail`, `e-mails` | `email` |
| `inbox`, `unread`, `mail`, `postfach` | `email` |
| `ungelesen`, `ungelesene`, `ungelesener`, `ungelesenes` | `email` |
| `calendar`, `kalender` | `calendar` |
| `termine`, `termin` | `calendar` |
| `appointment`, `appointments`, `meeting` | `calendar` |

## Adding New Keywords

Edit `ROUTER_KEYWORD_HINTS` in `src/business_assistant/config/constants.py`:

```python
ROUTER_KEYWORD_HINTS: dict[str, str] = {
    "email": "email",
    "new_keyword": "target_category",
    ...
}
```

The category value must match a registered plugin category name. Keywords are matched case-insensitively against individual words in the message.

## Debugging

When keyword hints add categories that the AI missed, a log line is emitted:

```
Keyword hints boosted categories: {'email'}
```

This appears in the application log before the final routing result.

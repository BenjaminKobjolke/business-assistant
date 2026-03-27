# Voice Message Routing Issues

## Problem

When users send voice messages, the bot transcribes the audio to text and routes it to the appropriate plugin. Two issues were discovered that caused voice-based queries to fail while identical typed queries worked correctly.

## Issue 1: Router received metadata instead of user intent

**Symptom:** Voice message asking "welche Termine habe ich heute?" (calendar query) got no calendar tools.

**Root cause:** The category router received the full `agent_text` including `[AUDIO MODE ACTIVE ...]` prefix, `[File received: ...]` metadata, `[File processed by transcribe: Transcription: ...]` wrapper, and raw upload URLs. The small router model (Qwen 2.5:7b) couldn't extract the actual user intent from all this noise.

**Fix:** `handler.py` now computes a separate `router_text` containing only the raw user intent:
- For voice messages (transcriptions exist and `message.text` is empty or a URL): uses the first transcription text
- For typed messages: uses `message.text` directly
- The full `agent_text` with all metadata is still passed to the AI agent

**Note:** XMPP voice messages set `message.text` to the upload URL (e.g., `https://xida.me:7443/...`), not empty string. The condition checks for URL-only text to correctly detect voice-only messages.

**File:** `src/business_assistant/bot/handler.py`

## Issue 2: Router model misclassified categories

**Symptom:** Voice message "Do I have unread emails?" routed to `web` instead of `email`, even with clean router text.

**Root cause:** The Qwen 2.5:7b model systematically confused "email" with "web". Improving the router prompt with more examples and explicit disambiguation did not fix it — the model is too small to reliably distinguish similar categories.

**Fix:** Added keyword-based category hints that supplement the AI router. When the message text contains known keywords (e.g., "email", "inbox", "unread"), the corresponding category is automatically added to the AI-selected categories. Keywords only add categories, never remove them.

**File:** `src/business_assistant/agent/router.py`, `src/business_assistant/config/constants.py`
**Docs:** `docs/ROUTER_KEYWORD_HINTS.md`

## Issue 3: Transcription quality

**Symptom:** Voice message intended as "habe ich ungelesene E-Mails" was transcribed as "habe ich ungelesene E-Mance". The garbled keyword didn't match any hints.

**Root cause:** Speech-to-text (Whisper) sometimes produces incorrect transcriptions, especially for non-English words mixed with technical terms.

**Mitigation:** Added German-specific keywords like "ungelesene" (unread) to the keyword hints. When the email-specific word is garbled, the surrounding context words still trigger the correct category. This is a partial mitigation — fundamentally bad transcriptions cannot be fully compensated for.

**Limitations:** Keyword hints can only catch cases where at least one recognizable keyword survives transcription. If the entire query is garbled, routing will fail. Improving transcription model quality (larger Whisper model, language-specific tuning) would address this at the source.

## Summary of changes

| File | Change |
|------|--------|
| `src/business_assistant/bot/handler.py` | Pass clean `router_text` to router instead of full `agent_text` |
| `src/business_assistant/agent/router.py` | Add `_apply_keyword_hints()` method for keyword-based category boosting |
| `src/business_assistant/config/constants.py` | Add `ROUTER_KEYWORD_HINTS` dict with email/calendar keywords |
| `tests/test_bot_handler_attachments.py` | Tests for voice message routing with clean text |
| `tests/test_router.py` | Tests for keyword hint boosting |

"""Integration test — real OpenAI API, mocked IMAP.

Verifies the full reply workflow:
1. Agent reads inbox and reports the latest email
2. Agent drafts a reply (shows it, does NOT save yet)
3. Agent saves the draft only when told to

Requires OPENAI_API_KEY in .env or environment. Skipped otherwise.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from bot_commander.types import BotMessage
from business_assistant_imap.plugin import register
from dotenv import load_dotenv

from business_assistant.agent.agent import create_agent
from business_assistant.bot.handler import AIMessageHandler
from business_assistant.config.settings import AppSettings, OpenAISettings, XmppSettings
from business_assistant.memory.store import MemoryStore
from business_assistant.plugins.registry import PluginRegistry

# ---------------------------------------------------------------------------
# Load .env so OPENAI_API_KEY / OPENAI_MODEL are available
# ---------------------------------------------------------------------------
load_dotenv()

_HAS_KEY = bool(os.environ.get("OPENAI_API_KEY"))


# ---------------------------------------------------------------------------
# Fake email helpers (mirrors imap-plugin test conftest)
# ---------------------------------------------------------------------------
class _FakeRawMessage:
    def __init__(self, headers: dict[str, str] | None = None) -> None:
        self._headers = headers or {}

    def get(self, key: str, default: str = "") -> str:
        return self._headers.get(key, default)


class _FakeEmailMessage:
    """Minimal stand-in for imap-client-lib EmailMessage."""

    def __init__(
        self,
        message_id: str = "123",
        from_address: str = "sender@example.com",
        to_address: str = "",
        subject: str = "Test Subject",
        date: str = "Mon, 09 Mar 2026 10:00:00 +0100",
        body_plain: str = "Hello, this is a test email.",
        body_html: str = "",
        attachments: list | None = None,
    ):
        self.message_id = message_id
        self.from_address = from_address
        self.subject = subject
        self.date = date
        self._body_plain = body_plain
        self._body_html = body_html
        self.attachments = attachments or []
        self.raw_message = _FakeRawMessage(
            {"To": to_address, "From": from_address}
        )

    def get_body(self, content_type: str = "text/plain") -> str | None:
        if content_type == "text/plain":
            return self._body_plain
        if content_type == "text/html":
            return self._body_html
        return None


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------
INBOX_EMAIL = _FakeEmailMessage(
    message_id="100",
    from_address="Timm Kamleiter <kamleiter@dyadic-agency.com>",
    subject="Project Update",
    body_plain=(
        "Hallo Benjamin, hier ist das Update zum Projekt. "
        "Beste Grüße, Timm"
    ),
)

SENT_EMAIL = _FakeEmailMessage(
    message_id="200",
    from_address="benjamin@example.com",
    to_address="kamleiter@dyadic-agency.com",
    subject="Re: Project Update",
    body_plain="Hallo Timm, danke für die Info. Beste Grüße Benjamin",
)


# ---------------------------------------------------------------------------
# Mock wiring helper
# ---------------------------------------------------------------------------
def _build_mock_imap_client() -> MagicMock:
    """Return a pre-configured mock ImapClient."""
    client = MagicMock()
    client.connect.return_value = True
    client.disconnect.return_value = None
    client.save_draft.return_value = True

    # get_all_messages — used by list_inbox, show_email, draft_reply, etc.
    client.get_all_messages.return_value = [("100", INBOX_EMAIL)]

    def _get_messages(
        search_criteria=None,
        folder="INBOX",
        limit=None,
        include_attachments=False,
    ):
        if folder == "Sent":
            return [("200", SENT_EMAIL)]
        # Default: INBOX
        return [("100", INBOX_EMAIL)]

    client.get_messages.side_effect = _get_messages
    return client


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not _HAS_KEY, reason="OPENAI_API_KEY not set")
class TestDraftReplyFlow:
    """End-to-end draft-reply workflow using real OpenAI."""

    def test_draft_reply_flow(self, tmp_path: Path) -> None:
        # -- Build real stack --------------------------------------------------
        memory_file = str(tmp_path / "memory.json")
        chat_log = str(tmp_path / "chat.log")
        memory = MemoryStore(memory_file)

        settings = AppSettings(
            xmpp=XmppSettings(
                jid="bot@example.com",
                password="secret",
                default_receiver="user@example.com",
                allowed_jids=["user@example.com"],
            ),
            openai=OpenAISettings(
                api_key=os.environ["OPENAI_API_KEY"],
                model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
            ),
            memory_file=memory_file,
            chat_log_file=chat_log,
            plugin_names=["business_assistant_imap"],
            max_conversation_history=100,
        )

        mock_client = _build_mock_imap_client()

        # Patch ImapClient so EmailService._create_client returns our mock
        with patch(
            "business_assistant_imap.email_service.ImapClient",
            return_value=mock_client,
        ):
            # Register IMAP plugin (needs IMAP_SERVER env for load_email_settings)
            registry = PluginRegistry()
            with patch.dict(os.environ, {
                "IMAP_SERVER": "imap.fake.com",
                "IMAP_USERNAME": "user@fake.com",
                "IMAP_PASSWORD": "fake-pass",
                "SMTP_SERVER": "smtp.fake.com",
                "EMAIL_FROM_ADDRESS": "benjamin@example.com",
            }):
                register(registry)

            model_name = f"openai:{settings.openai.model}"
            agent = create_agent(registry, memory, model_name)

            handler = AIMessageHandler(
                agent=agent,
                memory=memory,
                settings=settings,
                plugin_data=registry.plugin_data,
            )

            # -- Step 1: Ask about latest inbox email -------------------------
            r1 = handler.handle(
                BotMessage(
                    user_id="user@example.com",
                    text="What is the latest email in my inbox?",
                )
            )
            text1 = r1.text.lower()
            assert "project update" in text1 or "kamleiter" in text1, (
                f"Step 1 failed — expected email info, got: {r1.text}"
            )

            # -- Step 2: Ask to draft a reply ---------------------------------
            mock_client.save_draft.reset_mock()
            r2 = handler.handle(
                BotMessage(
                    user_id="user@example.com",
                    text=(
                        "Draft a reply to that email. "
                        "Tell them I am available on Monday at 2pm."
                    ),
                )
            )
            text2 = r2.text.lower()

            # Agent should show a draft, NOT save it yet
            assert "monday" in text2 or "montag" in text2, (
                f"Step 2 failed — draft should mention Monday, got: {r2.text}"
            )
            assert mock_client.save_draft.call_count == 0, (
                "Step 2 failed — save_draft should NOT be called yet"
            )

            # -- Step 3: Tell agent to save the draft -------------------------
            r3 = handler.handle(
                BotMessage(
                    user_id="user@example.com",
                    text="Save draft",
                )
            )

            assert mock_client.save_draft.call_count >= 1, (
                f"Step 3 failed — save_draft was not called. Response: {r3.text}"
            )

            # Verify saved draft content contains the key details
            call_kwargs = mock_client.save_draft.call_args
            draft_body = (
                call_kwargs.kwargs.get("body", "")
                if call_kwargs.kwargs
                else call_kwargs[1].get("body", "")
                if len(call_kwargs) > 1
                else ""
            )
            # Fall back to positional args if needed
            if not draft_body and call_kwargs.args:
                # save_draft(to_addresses, subject, body, ...)
                for arg in call_kwargs.args:
                    if isinstance(arg, str) and len(arg) > 50:
                        draft_body = arg
                        break

            draft_lower = draft_body.lower()
            assert "monday" in draft_lower or "montag" in draft_lower or "2" in draft_lower, (
                f"Step 3 failed — draft body should mention Monday/2pm. "
                f"Body: {draft_body[:200]}"
            )

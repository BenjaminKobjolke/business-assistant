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
from business_assistant_imap.plugin import register
from dotenv import load_dotenv

from business_assistant.agent.agent import create_agent
from business_assistant.agent.deps import Deps
from business_assistant.config.settings import AppSettings, OpenAISettings, XmppSettings
from business_assistant.memory.store import MemoryStore
from business_assistant.plugins.registry import PluginRegistry

from .conftest import FakeEmailMessage

# ---------------------------------------------------------------------------
# Load .env so OPENAI_API_KEY / OPENAI_MODEL are available
# ---------------------------------------------------------------------------
load_dotenv()

_HAS_KEY = bool(os.environ.get("OPENAI_API_KEY"))


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------
INBOX_EMAIL = FakeEmailMessage(
    message_id="100",
    from_address="Timm Kamleiter <kamleiter@dyadic-agency.com>",
    subject="Project Update",
    body_plain=(
        "Hallo Benjamin, hier ist das Update zum Projekt. "
        "Beste Grüße, Timm"
    ),
)

SENT_EMAIL = FakeEmailMessage(
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
            chat_log_file=str(tmp_path / "chat.log"),
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

            deps = Deps(
                memory=memory,
                settings=settings,
                user_id="user@example.com",
                plugin_data=registry.plugin_data,
            )

            # -- Step 1: Ask about latest inbox email -------------------------
            r1 = agent.run_sync(
                "What is the latest email in my inbox?",
                deps=deps,
            )
            text1 = r1.output.lower()
            assert "project update" in text1 or "kamleiter" in text1, (
                f"Step 1 failed — expected email info, got: {r1.output}"
            )

            # -- Step 2: Ask to draft a reply ---------------------------------
            mock_client.save_draft.reset_mock()
            r2 = agent.run_sync(
                (
                    "Draft a reply to that email. "
                    "Tell them I am available on Monday at 2pm."
                ),
                deps=deps,
                message_history=r1.all_messages(),
            )
            text2 = r2.output.lower()

            # Agent should show a draft, NOT save it yet
            assert "monday" in text2 or "montag" in text2, (
                f"Step 2 failed — draft should mention Monday, got: {r2.output}"
            )
            assert mock_client.save_draft.call_count == 0, (
                "Step 2 failed — save_draft should NOT be called yet"
            )

            # -- Step 3: Tell agent to save the draft -------------------------
            r3 = agent.run_sync(
                "Save draft",
                deps=deps,
                message_history=r2.all_messages(),
            )

            assert mock_client.save_draft.call_count >= 1, (
                f"Step 3 failed — save_draft was not called. Response: {r3.output}"
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

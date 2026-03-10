"""Integration test — real OpenAI API, mocked IMAP + FTP.

Verifies the AI calls get_attachment_url when the user asks to see an image:
1. Agent fetches the email and discovers the image attachment
2. Agent calls get_attachment_url (which uploads via FTP mock)
3. Agent shares the resulting URL with the user

Requires OPENAI_API_KEY in .env or environment. Skipped otherwise.
"""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
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
# Known FTP URL returned by mock
# ---------------------------------------------------------------------------
FAKE_FTP_URL = "https://cdn.example.com/abc12345_screenshot.png"


# ---------------------------------------------------------------------------
# Test data — email with an image attachment
# ---------------------------------------------------------------------------
_FAKE_ATTACHMENT = SimpleNamespace(
    filename="screenshot.png",
    content_type="image/png",
    data=b"\x89PNG fake image data",
    content_id=None,
    is_inline=False,
)

INBOX_EMAIL = FakeEmailMessage(
    message_id="300",
    from_address="alice@example.com",
    subject="Here is the screenshot",
    body_plain="Hi, please find the screenshot attached.",
    attachments=[_FAKE_ATTACHMENT],
)


# ---------------------------------------------------------------------------
# Mock wiring helper
# ---------------------------------------------------------------------------
def _build_mock_imap_client() -> MagicMock:
    """Return a pre-configured mock ImapClient with attachment support."""
    client = MagicMock()
    client.connect.return_value = True
    client.disconnect.return_value = None

    client.get_all_messages.return_value = [("300", INBOX_EMAIL)]

    def _get_messages(
        search_criteria=None,
        folder="INBOX",
        limit=None,
        include_attachments=False,
    ):
        return [("300", INBOX_EMAIL)]

    client.get_messages.side_effect = _get_messages
    return client


# ---------------------------------------------------------------------------
# Refusal phrases the AI should NOT use
# ---------------------------------------------------------------------------
_REFUSAL_PHRASES = [
    "kann ich nicht",
    "cannot display",
    "can't display",
    "can't show",
    "cannot show",
    "nicht anzeigen",
    "nicht möglich",
    "unable to display",
    "unable to show",
]


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not _HAS_KEY, reason="OPENAI_API_KEY not set")
class TestAttachmentUrlFlow:
    """End-to-end: AI uploads attachment via FTP and shares URL."""

    def test_show_image_calls_get_attachment_url(self, tmp_path: Path) -> None:
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
        mock_ftp = MagicMock()
        mock_ftp.upload.return_value = FAKE_FTP_URL

        with patch(
            "business_assistant_imap.email_service.ImapClient",
            return_value=mock_client,
        ):
            plugin_data: dict = {"ftp_upload": mock_ftp}

            registry = PluginRegistry(plugin_data=plugin_data)
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
                plugin_data=plugin_data,
            )

            # -- Ask the AI to show the image (direct run_sync) ----------------
            result = agent.run_sync(
                "Show me the image from the latest email",
                deps=deps,
            )
            response_text = result.output

            # -- Assertion 1: get_attachment_url was called (FTP upload) --------
            assert mock_ftp.upload.call_count >= 1, (
                f"get_attachment_url was never called (FTP upload not invoked). "
                f"Response: {response_text}"
            )

            # -- Assertion 2: URL appears in the response ----------------------
            assert FAKE_FTP_URL in response_text, (
                f"Expected URL '{FAKE_FTP_URL}' in response, got: {response_text}"
            )

            # -- Assertion 3: No refusal phrases in response -------------------
            text_lower = response_text.lower()
            for phrase in _REFUSAL_PHRASES:
                assert phrase not in text_lower, (
                    f"AI refused with '{phrase}' instead of using "
                    f"get_attachment_url. Response: {response_text}"
                )

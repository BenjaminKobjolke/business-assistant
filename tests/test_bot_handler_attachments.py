"""Tests for attachment processing in AIMessageHandler."""

from __future__ import annotations

from unittest.mock import MagicMock

from bot_commander.types import Attachment, BotMessage

from business_assistant.config.constants import PLUGIN_DATA_FILE_HANDLERS
from business_assistant.files.downloader import DownloadedFile, FileDownloader
from business_assistant.files.handler_registry import FileHandlerRegistry, FileHandlerResult
from tests.test_bot_handler import _make_handler


class TestAttachmentProcessing:
    def test_no_attachments_no_prefix(self, tmp_memory_file: str) -> None:
        handler = _make_handler(agent_result="Hi!", tmp_memory_file=tmp_memory_file)
        msg = BotMessage(user_id="user@test.com", text="hello")
        assert handler._process_attachments(msg) == ""

    def test_no_downloader_no_prefix(self, tmp_memory_file: str) -> None:
        att = Attachment(url="https://example.com/f.ogg", filename="f.ogg", mime_type="audio/ogg")
        handler = _make_handler(agent_result="Hi!", tmp_memory_file=tmp_memory_file)
        msg = BotMessage(user_id="user@test.com", text="hello", attachments=(att,))
        assert handler._process_attachments(msg) == ""

    def test_attachment_downloaded_and_prefix_added(self, tmp_memory_file: str) -> None:
        mock_downloader = MagicMock(spec=FileDownloader)
        mock_downloader.download.return_value = DownloadedFile(
            path="data/uploads/20260310_abc_voice.ogg",
            filename="voice.ogg",
            mime_type="audio/ogg",
            size=45320,
        )

        handler = _make_handler(
            agent_result="Got it!",
            tmp_memory_file=tmp_memory_file,
            file_downloader=mock_downloader,
        )
        att = Attachment(
            url="https://upload.example.com/voice.ogg",
            filename="voice.ogg",
            mime_type="audio/ogg",
        )
        msg = BotMessage(user_id="user@test.com", text="check this", attachments=(att,))

        response = handler.handle(msg)
        assert response.text == "Got it!"

        # Verify the agent received the file prefix
        call_args = handler._agent.run_sync.call_args
        agent_text = call_args[0][0]
        assert "[File received: voice.ogg" in agent_text
        assert "45320 bytes" in agent_text
        assert "check this" in agent_text

    def test_attachment_with_file_handler(self, tmp_memory_file: str) -> None:
        mock_downloader = MagicMock(spec=FileDownloader)
        mock_downloader.download.return_value = DownloadedFile(
            path="data/uploads/20260310_abc_voice.ogg",
            filename="voice.ogg",
            mime_type="audio/ogg",
            size=1000,
        )

        file_registry = FileHandlerRegistry()
        file_registry.register(
            ["audio/*"],
            "audio-plugin",
            lambda df, uid: FileHandlerResult(summary='Transcription: "Hello"'),
        )
        plugin_data = {PLUGIN_DATA_FILE_HANDLERS: file_registry}

        handler = _make_handler(
            agent_result="OK",
            tmp_memory_file=tmp_memory_file,
            file_downloader=mock_downloader,
            plugin_data=plugin_data,
        )
        att = Attachment(
            url="https://example.com/voice.ogg",
            filename="voice.ogg",
            mime_type="audio/ogg",
        )
        msg = BotMessage(user_id="user@test.com", text="", attachments=(att,))

        handler.handle(msg)

        agent_text = handler._agent.run_sync.call_args[0][0]
        assert "[File processed by audio-plugin:" in agent_text
        assert 'Transcription: "Hello"' in agent_text

    def test_download_failure_skips_attachment(self, tmp_memory_file: str) -> None:
        mock_downloader = MagicMock(spec=FileDownloader)
        mock_downloader.download.side_effect = OSError("connection refused")

        handler = _make_handler(
            agent_result="OK",
            tmp_memory_file=tmp_memory_file,
            file_downloader=mock_downloader,
        )
        att = Attachment(url="https://example.com/f.ogg", filename="f.ogg", mime_type="audio/ogg")
        msg = BotMessage(user_id="user@test.com", text="hi", attachments=(att,))

        response = handler.handle(msg)
        assert response.text == "OK"

        # Agent should receive just the original text (no prefix)
        agent_text = handler._agent.run_sync.call_args[0][0]
        assert agent_text == "hi"

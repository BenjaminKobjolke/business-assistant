"""Tests for attachment processing in AIMessageHandler."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from bot_commander.types import Attachment, BotMessage, BotResponse
from pydantic_ai.usage import RunUsage

from business_assistant.agent.router import CategoryRouter, RoutingResult
from business_assistant.bot.handler import AIMessageHandler
from business_assistant.bot.handler_deps import HandlerDeps
from business_assistant.config.constants import (
    PLUGIN_DATA_COMMAND_HANDLERS,
    PLUGIN_DATA_FILE_HANDLERS,
)
from business_assistant.files.downloader import DownloadedFile, FileDownloader
from business_assistant.files.handler_registry import FileHandlerRegistry, FileHandlerResult
from business_assistant.memory.store import MemoryStore
from business_assistant.plugins.registry import PluginRegistry
from tests.conftest import make_test_settings
from tests.test_bot_handler import _make_handler


class TestAttachmentProcessing:
    def test_no_attachments_no_prefix(self, tmp_memory_file: str) -> None:
        handler = _make_handler(agent_result="Hi!", tmp_memory_file=tmp_memory_file)
        msg = BotMessage(user_id="user@test.com", text="hello")
        assert handler._process_attachments(msg) == ("", [])

    def test_no_downloader_no_prefix(self, tmp_memory_file: str) -> None:
        att = Attachment(url="https://example.com/f.ogg", filename="f.ogg", mime_type="audio/ogg")
        handler = _make_handler(agent_result="Hi!", tmp_memory_file=tmp_memory_file)
        msg = BotMessage(user_id="user@test.com", text="hello", attachments=(att,))
        assert handler._process_attachments(msg) == ("", [])

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

    def test_voice_command_triggers_command_handler(self, tmp_memory_file: str) -> None:
        """Voice-only message whose transcription matches a command should short-circuit."""
        mock_downloader = MagicMock(spec=FileDownloader)
        mock_downloader.download.return_value = DownloadedFile(
            path="data/uploads/voice.ogg",
            filename="voice.ogg",
            mime_type="audio/ogg",
            size=1000,
        )

        file_registry = FileHandlerRegistry()
        file_registry.register(
            ["audio/*"],
            "transcribe",
            lambda df, uid: FileHandlerResult(
                summary="Transcription: audio mode on",
            ),
        )

        def _cmd_handler(
            text: str, user_id: str, plugin_data: dict,
        ) -> BotResponse | None:
            if text.lower().strip() == "audio mode on":
                return BotResponse(text="Audio enabled!")
            return None

        plugin_data = {
            PLUGIN_DATA_FILE_HANDLERS: file_registry,
            PLUGIN_DATA_COMMAND_HANDLERS: [_cmd_handler],
        }

        handler = _make_handler(
            agent_result="Should not reach AI",
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

        response = handler.handle(msg)
        assert response.text == "Audio enabled!"
        handler._agent.run_sync.assert_not_called()

    def test_voice_command_with_trailing_punctuation(self, tmp_memory_file: str) -> None:
        """Transcription with trailing punctuation should still match a command."""
        mock_downloader = MagicMock(spec=FileDownloader)
        mock_downloader.download.return_value = DownloadedFile(
            path="data/uploads/voice.ogg",
            filename="voice.ogg",
            mime_type="audio/ogg",
            size=1000,
        )

        file_registry = FileHandlerRegistry()
        file_registry.register(
            ["audio/*"],
            "transcribe",
            lambda df, uid: FileHandlerResult(
                summary="Transcription: Audio mode on.",
            ),
        )

        def _cmd_handler(
            text: str, user_id: str, plugin_data: dict,
        ) -> BotResponse | None:
            if text.lower().strip() == "audio mode on":
                return BotResponse(text="Audio enabled!")
            return None

        plugin_data = {
            PLUGIN_DATA_FILE_HANDLERS: file_registry,
            PLUGIN_DATA_COMMAND_HANDLERS: [_cmd_handler],
        }

        handler = _make_handler(
            agent_result="Should not reach AI",
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

        response = handler.handle(msg)
        assert response.text == "Audio enabled!"
        handler._agent.run_sync.assert_not_called()

    def test_voice_transcription_not_command_goes_to_ai(self, tmp_memory_file: str) -> None:
        """Voice-only message with non-command transcription should reach the AI."""
        mock_downloader = MagicMock(spec=FileDownloader)
        mock_downloader.download.return_value = DownloadedFile(
            path="data/uploads/voice.ogg",
            filename="voice.ogg",
            mime_type="audio/ogg",
            size=1000,
        )

        file_registry = FileHandlerRegistry()
        file_registry.register(
            ["audio/*"],
            "transcribe",
            lambda df, uid: FileHandlerResult(
                summary="Transcription: What is the weather?",
            ),
        )

        handler = _make_handler(
            agent_result="It is sunny!",
            tmp_memory_file=tmp_memory_file,
            file_downloader=mock_downloader,
            plugin_data={PLUGIN_DATA_FILE_HANDLERS: file_registry},
        )
        att = Attachment(
            url="https://example.com/voice.ogg",
            filename="voice.ogg",
            mime_type="audio/ogg",
        )
        msg = BotMessage(user_id="user@test.com", text="", attachments=(att,))

        response = handler.handle(msg)
        assert response.text == "It is sunny!"
        handler._agent.run_sync.assert_called_once()

    def test_typed_text_with_attachment_skips_voice_command_check(
        self, tmp_memory_file: str,
    ) -> None:
        """When the user types text alongside a voice attachment, skip voice command check."""
        mock_downloader = MagicMock(spec=FileDownloader)
        mock_downloader.download.return_value = DownloadedFile(
            path="data/uploads/voice.ogg",
            filename="voice.ogg",
            mime_type="audio/ogg",
            size=1000,
        )

        file_registry = FileHandlerRegistry()
        file_registry.register(
            ["audio/*"],
            "transcribe",
            lambda df, uid: FileHandlerResult(
                summary="Transcription: clear",
            ),
        )

        handler = _make_handler(
            agent_result="Got it!",
            tmp_memory_file=tmp_memory_file,
            file_downloader=mock_downloader,
            plugin_data={PLUGIN_DATA_FILE_HANDLERS: file_registry},
        )
        att = Attachment(
            url="https://example.com/voice.ogg",
            filename="voice.ogg",
            mime_type="audio/ogg",
        )
        # User typed text alongside the audio — voice command check should be skipped
        msg = BotMessage(
            user_id="user@test.com", text="check this file", attachments=(att,),
        )

        response = handler.handle(msg)
        assert response.text == "Got it!"
        handler._agent.run_sync.assert_called_once()

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


class TestVoiceMessageRouting:
    """Router should receive clean transcription text, not file metadata."""

    @staticmethod
    def _make_routed_handler_with_transcription(
        tmp_memory_file: str,
        tmp_path: Path,
        transcription: str,
    ) -> tuple[AIMessageHandler, MagicMock]:
        """Create a handler with router, file downloader, and transcription handler."""
        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.output = "OK"
        mock_result.all_messages.return_value = [{"role": "user"}, {"role": "assistant"}]
        mock_result.usage.return_value = RunUsage()
        mock_agent.run_sync.return_value = mock_result

        mock_router = MagicMock(spec=CategoryRouter)
        mock_router.route.return_value = RoutingResult(
            categories={"calendar"}, usage=None,
        )

        mock_registry = MagicMock(spec=PluginRegistry)
        mock_registry.tools_for_categories.return_value = []
        mock_registry.prompts_for_categories.return_value = ""

        mock_downloader = MagicMock(spec=FileDownloader)
        mock_downloader.download.return_value = DownloadedFile(
            path="data/uploads/voice.m4a",
            filename="voice.m4a",
            mime_type="audio/mp4",
            size=12000,
        )

        file_registry = FileHandlerRegistry()
        file_registry.register(
            ["audio/*"],
            "transcribe",
            lambda df, uid: FileHandlerResult(
                summary=f"Transcription: {transcription}",
            ),
        )

        memory = MemoryStore(tmp_memory_file)
        log_dir = str(tmp_path / "chats")
        settings = make_test_settings(chat_log_dir=log_dir)

        handler = AIMessageHandler(HandlerDeps(
            agent=mock_agent,
            memory=memory,
            settings=settings,
            registry=mock_registry,
            router=mock_router,
            core_tools=[],
            file_downloader=mock_downloader,
            plugin_data={PLUGIN_DATA_FILE_HANDLERS: file_registry},
        ))
        return handler, mock_router

    def test_voice_message_router_receives_transcription_text(
        self, tmp_memory_file: str, tmp_path: Path,
    ) -> None:
        """Voice-only message: router should get clean transcription, not metadata."""
        handler, mock_router = self._make_routed_handler_with_transcription(
            tmp_memory_file, tmp_path,
            transcription="welche Termine habe ich heute?",
        )
        att = Attachment(
            url="https://example.com/voice.m4a",
            filename="voice.m4a",
            mime_type="audio/mp4",
        )
        msg = BotMessage(user_id="user@test.com", text="", attachments=(att,))

        handler.handle(msg)

        router_text = mock_router.route.call_args[0][0]
        assert router_text == "welche Termine habe ich heute?"
        assert "[File received:" not in router_text
        assert "[File processed" not in router_text

    def test_typed_message_with_attachment_router_receives_typed_text(
        self, tmp_memory_file: str, tmp_path: Path,
    ) -> None:
        """Typed message with attachment: router should get typed text, not metadata."""
        handler, mock_router = self._make_routed_handler_with_transcription(
            tmp_memory_file, tmp_path,
            transcription="some audio content",
        )
        att = Attachment(
            url="https://example.com/voice.m4a",
            filename="voice.m4a",
            mime_type="audio/mp4",
        )
        msg = BotMessage(
            user_id="user@test.com", text="check my calendar", attachments=(att,),
        )

        handler.handle(msg)

        router_text = mock_router.route.call_args[0][0]
        assert router_text == "check my calendar"

    def test_voice_message_with_url_text_router_receives_transcription(
        self, tmp_memory_file: str, tmp_path: Path,
    ) -> None:
        """XMPP voice messages have upload URL as message.text — router should
        get the transcription, not the URL."""
        handler, mock_router = self._make_routed_handler_with_transcription(
            tmp_memory_file, tmp_path,
            transcription="Do I have unread emails?",
        )
        att = Attachment(
            url="https://xida.me:7443/httpfileupload/abc/voice.m4a",
            filename="voice.m4a",
            mime_type="audio/mp4",
        )
        msg = BotMessage(
            user_id="user@test.com",
            text="https://xida.me:7443/httpfileupload/abc/voice.m4a",
            attachments=(att,),
        )

        handler.handle(msg)

        router_text = mock_router.route.call_args[0][0]
        assert router_text == "Do I have unread emails?"
        assert "https://" not in router_text
        assert "[File received:" not in router_text

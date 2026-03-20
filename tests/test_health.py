"""Tests for health check functions."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from business_assistant.bot.health import check_ollama_health


class TestCheckOllamaHealth:
    @patch("business_assistant.bot.health.urllib.request.urlopen")
    def test_success(self, mock_urlopen: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"Ollama is running"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        assert check_ollama_health("http://localhost:11434/v1") is True

    @patch("business_assistant.bot.health.urllib.request.urlopen")
    def test_connection_error(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = ConnectionError("refused")

        assert check_ollama_health("http://localhost:11434/v1") is False

    @patch("business_assistant.bot.health.urllib.request.urlopen")
    def test_strips_v1_suffix(self, mock_urlopen: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"Ollama is running"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        check_ollama_health("http://localhost:11434/v1")

        req = mock_urlopen.call_args.args[0]
        assert req.full_url == "http://localhost:11434"

    @patch("business_assistant.bot.health.urllib.request.urlopen")
    def test_no_v1_suffix(self, mock_urlopen: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"Ollama is running"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        check_ollama_health("http://localhost:11434")

        req = mock_urlopen.call_args.args[0]
        assert req.full_url == "http://localhost:11434"

    @patch("business_assistant.bot.health.urllib.request.urlopen")
    def test_unexpected_response(self, mock_urlopen: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"Not Found"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        assert check_ollama_health("http://localhost:11434/v1") is False

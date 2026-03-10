"""Tests for FileDownloader."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from business_assistant.files.downloader import (
    DownloadedFile,
    FileDownloader,
    _sanitize_filename,
)


class TestSanitizeFilename:
    def test_normal_filename(self) -> None:
        assert _sanitize_filename("voice.ogg") == "voice.ogg"

    def test_strips_path_separators(self) -> None:
        assert "/" not in _sanitize_filename("path/to/file.txt")
        assert "\\" not in _sanitize_filename("path\\to\\file.txt")

    def test_strips_unsafe_chars(self) -> None:
        result = _sanitize_filename('file<>:"|?*.txt')
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result
        assert '"' not in result
        assert "?" not in result
        assert "*" not in result

    def test_limits_length(self) -> None:
        long_name = "a" * 200 + ".txt"
        result = _sanitize_filename(long_name)
        assert len(result) <= 80

    def test_empty_returns_file(self) -> None:
        assert _sanitize_filename("") == "file"


class TestDownloadedFile:
    def test_create(self) -> None:
        df = DownloadedFile(
            path="data/uploads/f.ogg", filename="f.ogg",
            mime_type="audio/ogg", size=100,
        )
        assert df.path == "data/uploads/f.ogg"
        assert df.filename == "f.ogg"
        assert df.mime_type == "audio/ogg"
        assert df.size == 100

    def test_frozen(self) -> None:
        df = DownloadedFile(path="p", filename="f", mime_type="m", size=0)
        with pytest.raises(AttributeError):
            df.path = "other"  # type: ignore[misc]


class TestFileDownloader:
    def test_creates_upload_dir(self, tmp_path) -> None:
        upload_dir = tmp_path / "uploads"
        FileDownloader(str(upload_dir))
        assert upload_dir.is_dir()

    def test_download_success(self, tmp_path) -> None:
        upload_dir = tmp_path / "uploads"
        downloader = FileDownloader(str(upload_dir))

        mock_resp = MagicMock()
        mock_resp.read.return_value = b"fake audio data"
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        urlopen = "business_assistant.files.downloader.urllib.request.urlopen"
        with patch(urlopen, return_value=mock_resp):
            result = downloader.download(
                "https://upload.example.com/voice.ogg", "voice.ogg", "audio/ogg"
            )

        assert isinstance(result, DownloadedFile)
        assert result.filename == "voice.ogg"
        assert result.mime_type == "audio/ogg"
        assert result.size == 15
        assert "voice.ogg" in result.path

    def test_download_unique_names(self, tmp_path) -> None:
        upload_dir = tmp_path / "uploads"
        downloader = FileDownloader(str(upload_dir))

        mock_resp = MagicMock()
        mock_resp.read.return_value = b"data"
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        urlopen = "business_assistant.files.downloader.urllib.request.urlopen"
        with patch(urlopen, return_value=mock_resp):
            r1 = downloader.download("https://example.com/a.txt", "a.txt", "text/plain")
            r2 = downloader.download("https://example.com/a.txt", "a.txt", "text/plain")

        assert r1.path != r2.path

    def test_download_no_filename(self, tmp_path) -> None:
        upload_dir = tmp_path / "uploads"
        downloader = FileDownloader(str(upload_dir))

        mock_resp = MagicMock()
        mock_resp.read.return_value = b"data"
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        urlopen = "business_assistant.files.downloader.urllib.request.urlopen"
        with patch(urlopen, return_value=mock_resp):
            result = downloader.download("https://example.com/file", "", "")

        assert result.filename == "file"

    def test_download_failure_raises(self, tmp_path) -> None:
        upload_dir = tmp_path / "uploads"
        downloader = FileDownloader(str(upload_dir))

        with (
            patch(
                "business_assistant.files.downloader.urllib.request.urlopen",
                side_effect=OSError("connection refused"),
            ),
            pytest.raises(OSError, match="connection refused"),
        ):
            downloader.download("https://example.com/file.txt", "file.txt", "text/plain")

"""Tests for FtpUploadService."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from business_assistant.config.settings import FtpSettings
from business_assistant.upload.ftp_service import FtpUploadService


@pytest.fixture()
def ftp_settings() -> FtpSettings:
    return FtpSettings(
        host="ftp.example.com",
        username="user",
        password="pass",
        base_path="/uploads",
        base_url="https://cdn.example.com/uploads",
        port=21,
        use_tls=True,
    )


@pytest.fixture()
def ftp_settings_plain() -> FtpSettings:
    return FtpSettings(
        host="ftp.example.com",
        username="user",
        password="pass",
        base_path="/uploads",
        base_url="https://cdn.example.com/uploads",
        port=21,
        use_tls=False,
    )


class TestFtpUploadService:
    @patch("business_assistant.upload.ftp_service.ftplib")
    def test_upload_tls(
        self, mock_ftplib: MagicMock, ftp_settings: FtpSettings
    ) -> None:
        mock_ftp = MagicMock()
        mock_ftplib.FTP_TLS.return_value = mock_ftp

        service = FtpUploadService(ftp_settings)
        url = service.upload(b"file-content", "report.pdf")

        mock_ftplib.FTP_TLS.assert_called_once()
        mock_ftp.connect.assert_called_once_with("ftp.example.com", 21)
        mock_ftp.login.assert_called_once_with("user", "pass")
        mock_ftp.prot_p.assert_called_once()
        mock_ftp.storbinary.assert_called_once()
        mock_ftp.quit.assert_called_once()

        assert url.startswith("https://cdn.example.com/uploads/")
        assert url.endswith("_report.pdf")

    @patch("business_assistant.upload.ftp_service.ftplib")
    def test_upload_plain_ftp(
        self, mock_ftplib: MagicMock, ftp_settings_plain: FtpSettings
    ) -> None:
        mock_ftp = MagicMock()
        mock_ftplib.FTP.return_value = mock_ftp

        service = FtpUploadService(ftp_settings_plain)
        url = service.upload(b"file-content", "image.png")

        mock_ftplib.FTP.assert_called_once()
        mock_ftplib.FTP_TLS.assert_not_called()
        mock_ftp.prot_p.assert_not_called()
        mock_ftp.connect.assert_called_once_with("ftp.example.com", 21)
        mock_ftp.login.assert_called_once_with("user", "pass")
        mock_ftp.storbinary.assert_called_once()
        mock_ftp.quit.assert_called_once()

        assert url.startswith("https://cdn.example.com/uploads/")
        assert url.endswith("_image.png")

    @patch("business_assistant.upload.ftp_service.ftplib")
    def test_url_format(self, mock_ftplib: MagicMock, ftp_settings: FtpSettings) -> None:
        mock_ftp = MagicMock()
        mock_ftplib.FTP_TLS.return_value = mock_ftp

        service = FtpUploadService(ftp_settings)
        url = service.upload(b"data", "test.txt")

        # URL has format: base_url/8hex_filename
        parts = url.rsplit("/", 1)
        assert parts[0] == "https://cdn.example.com/uploads"
        name_part = parts[1]
        assert name_part.endswith("_test.txt")
        prefix = name_part.replace("_test.txt", "")
        assert len(prefix) == 8

    @patch("business_assistant.upload.ftp_service.ftplib")
    def test_base_url_trailing_slash_stripped(
        self, mock_ftplib: MagicMock
    ) -> None:
        settings = FtpSettings(
            host="ftp.example.com",
            username="user",
            password="pass",
            base_path="/uploads",
            base_url="https://cdn.example.com/uploads/",
            port=21,
            use_tls=True,
        )
        mock_ftp = MagicMock()
        mock_ftplib.FTP_TLS.return_value = mock_ftp

        service = FtpUploadService(settings)
        url = service.upload(b"data", "file.txt")

        # Should not have double slash
        assert "//file" not in url
        assert url.startswith("https://cdn.example.com/uploads/")

    @patch("business_assistant.upload.ftp_service.ftplib")
    def test_upload_calls_quit_on_error(
        self, mock_ftplib: MagicMock, ftp_settings: FtpSettings
    ) -> None:
        mock_ftp = MagicMock()
        mock_ftplib.FTP_TLS.return_value = mock_ftp
        mock_ftp.storbinary.side_effect = OSError("upload failed")

        service = FtpUploadService(ftp_settings)
        with pytest.raises(OSError, match="upload failed"):
            service.upload(b"data", "file.txt")

        mock_ftp.quit.assert_called_once()

    @patch("business_assistant.upload.ftp_service.ftplib")
    def test_stor_command_uses_base_path(
        self, mock_ftplib: MagicMock, ftp_settings: FtpSettings
    ) -> None:
        mock_ftp = MagicMock()
        mock_ftplib.FTP_TLS.return_value = mock_ftp

        service = FtpUploadService(ftp_settings)
        service.upload(b"data", "file.txt")

        stor_cmd = mock_ftp.storbinary.call_args[0][0]
        assert stor_cmd.startswith("STOR /uploads/")
        assert stor_cmd.endswith("_file.txt")

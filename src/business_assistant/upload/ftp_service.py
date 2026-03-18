"""FTP upload service — uploads files and returns public URLs."""

from __future__ import annotations

import ftplib
import io
import logging
import uuid

from business_assistant.config.settings import FtpSettings

logger = logging.getLogger(__name__)


class FtpUploadService:
    """Upload binary data to an FTP server and return a public URL."""

    def __init__(self, settings: FtpSettings) -> None:
        self._settings = settings

    def upload(self, data: bytes, filename: str) -> str:
        """Upload data to FTP, return public URL.

        Generates unique remote path: {base_path}/{uuid}_{filename}
        Returns: {base_url}/{uuid}_{filename}
        """
        unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"
        remote_path = f"{self._settings.base_path}/{unique_name}"

        ftp_cls = ftplib.FTP_TLS if self._settings.use_tls else ftplib.FTP
        ftp = ftp_cls()
        try:
            ftp.connect(self._settings.host, self._settings.port)
            ftp.login(self._settings.username, self._settings.password)
            if self._settings.use_tls and isinstance(ftp, ftplib.FTP_TLS):
                ftp.prot_p()
            ftp.storbinary(f"STOR {remote_path}", io.BytesIO(data))
        finally:
            ftp.quit()

        base = self._settings.base_url.rstrip("/")
        return f"{base}/{unique_name}"

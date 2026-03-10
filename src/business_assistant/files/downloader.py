"""File downloader for XMPP file uploads."""

from __future__ import annotations

import logging
import re
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from business_assistant.config.constants import LOG_FILE_DOWNLOAD_FAILED, LOG_FILE_DOWNLOADED

logger = logging.getLogger(__name__)

_MAX_FILENAME_LEN = 80
_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


@dataclass(frozen=True)
class DownloadedFile:
    """Result of downloading a file attachment."""

    path: str
    filename: str
    mime_type: str
    size: int


def _sanitize_filename(name: str) -> str:
    """Remove path separators and unsafe characters, limit length."""
    name = name.replace("/", "_").replace("\\", "_")
    name = _UNSAFE_CHARS.sub("_", name)
    if len(name) > _MAX_FILENAME_LEN:
        name = name[-_MAX_FILENAME_LEN:]
    return name or "file"


class FileDownloader:
    """Downloads files from URLs to a local upload directory."""

    def __init__(self, upload_dir: str) -> None:
        self._upload_dir = Path(upload_dir)
        self._upload_dir.mkdir(parents=True, exist_ok=True)

    def download(self, url: str, filename: str = "", mime_type: str = "") -> DownloadedFile:
        """Download a URL to the upload directory with a unique name.

        Raises ``OSError`` on download failure.
        """
        safe_name = _sanitize_filename(filename) if filename else "file"
        date_prefix = datetime.now(tz=UTC).strftime("%Y%m%d")
        unique_id = uuid4().hex[:8]
        dest_name = f"{date_prefix}_{unique_id}_{safe_name}"
        dest_path = self._upload_dir / dest_name

        try:
            with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310
                data = resp.read()
            dest_path.write_bytes(data)
            size = len(data)
            logger.info(LOG_FILE_DOWNLOADED, dest_name, size)
            return DownloadedFile(
                path=str(dest_path),
                filename=filename or safe_name,
                mime_type=mime_type,
                size=size,
            )
        except Exception:
            logger.error(LOG_FILE_DOWNLOAD_FAILED, url, exc_info=True)
            raise

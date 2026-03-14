"""PID-based single-instance guard with auto-shutdown of old instances."""

from __future__ import annotations

import ctypes
import logging
import os
import time
from pathlib import Path

from business_assistant.config.constants import (
    ERR_PID_SHUTDOWN_TIMEOUT,
    LOG_PID_LOCK_ACQUIRED,
    LOG_PID_LOCK_RELEASED,
    LOG_PID_OLD_STOPPED,
    LOG_PID_SHUTTING_DOWN_OLD,
    LOG_PID_STALE,
    SHUTDOWN_FLAG_FILE,
)

logger = logging.getLogger(__name__)

_POLL_INTERVAL_SECONDS = 1
_DEFAULT_TIMEOUT_SECONDS = 30


class PidLockError(Exception):
    """Raised when the PID lock cannot be acquired."""


class PidLock:
    """Single-instance guard using a PID file.

    On ``acquire()``, if another instance is running, it creates
    ``shutdown.flag`` and waits for the old process to exit.
    """

    def __init__(self, pid_file: Path) -> None:
        self._pid_file = pid_file

    def acquire(self, timeout: int = _DEFAULT_TIMEOUT_SECONDS) -> None:
        """Acquire the PID lock, shutting down any existing instance first."""
        existing_pid = self._read_pid()
        if existing_pid is not None:
            if _is_process_alive(existing_pid):
                logger.info(LOG_PID_SHUTTING_DOWN_OLD, existing_pid)
                Path(SHUTDOWN_FLAG_FILE).touch()
                self._wait_for_exit(existing_pid, timeout)
                logger.info(LOG_PID_OLD_STOPPED)
            else:
                logger.info(LOG_PID_STALE, existing_pid)

        self._pid_file.write_text(str(os.getpid()))
        logger.info(LOG_PID_LOCK_ACQUIRED, os.getpid())

    def release(self) -> None:
        """Delete the PID file (idempotent)."""
        try:
            self._pid_file.unlink()
        except FileNotFoundError:
            pass
        else:
            logger.info(LOG_PID_LOCK_RELEASED)

    def _read_pid(self) -> int | None:
        """Read and parse the PID file, returning ``None`` for missing/corrupt files."""
        try:
            text = self._pid_file.read_text().strip()
            return int(text)
        except (FileNotFoundError, ValueError):
            return None

    def _wait_for_exit(self, pid: int, timeout: int) -> None:
        """Poll until the process exits or timeout is reached."""
        elapsed = 0
        while _is_process_alive(pid) and elapsed < timeout:
            time.sleep(_POLL_INTERVAL_SECONDS)
            elapsed += _POLL_INTERVAL_SECONDS
        if _is_process_alive(pid):
            raise PidLockError(
                ERR_PID_SHUTDOWN_TIMEOUT.format(pid=pid, timeout=timeout)
            )


def _is_process_alive(pid: int) -> bool:
    """Check whether a process with the given PID is still running (Windows)."""
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    handle = ctypes.windll.kernel32.OpenProcess(  # type: ignore[union-attr]
        PROCESS_QUERY_LIMITED_INFORMATION, False, pid
    )
    if handle:
        ctypes.windll.kernel32.CloseHandle(handle)  # type: ignore[union-attr]
        return True
    return False

"""Entry point for the business assistant."""

from __future__ import annotations

import atexit
import logging
import signal
import sys
import threading
import time
from pathlib import Path

from business_assistant.bot.app import Application
from business_assistant.config.constants import (
    LOG_APP_RESTARTING,
    LOG_APP_SHUTDOWN_FLAG,
    LOG_STALE_RESTART_FLAG,
    LOG_STALE_SHUTDOWN_FLAG,
    PID_LOCK_FILE,
    RESTART_FLAG_FILE,
    SHUTDOWN_FLAG_FILE,
)
from business_assistant.config.log_setup import setup_logging
from business_assistant.config.pidlock import PidLock, PidLockError

logger = logging.getLogger(__name__)


class _FlagWatcher:
    """Polls for restart/shutdown flag files and signals the stop event when found."""

    def __init__(
        self,
        restart_path: Path,
        shutdown_path: Path,
        stop_event: threading.Event,
    ) -> None:
        self._restart_path = restart_path
        self._shutdown_path = shutdown_path
        self._stop_event = stop_event
        self._start_time = time.time()
        self.restart_requested = False

    def _is_fresh(self, path: Path) -> bool:
        """Return True if *path* was modified after this watcher was created."""
        try:
            return path.stat().st_mtime > self._start_time
        except OSError:
            return False

    def watch(self) -> None:
        """Poll every 5 seconds for flag files."""
        while not self._stop_event.is_set():
            if self._shutdown_path.exists():
                if not self._is_fresh(self._shutdown_path):
                    logger.warning(LOG_STALE_SHUTDOWN_FLAG)
                    self._shutdown_path.unlink(missing_ok=True)
                else:
                    self._shutdown_path.unlink(missing_ok=True)
                    self.restart_requested = False
                    logger.info(LOG_APP_SHUTDOWN_FLAG)
                    self._stop_event.set()
                    return
            if self._restart_path.exists():
                if not self._is_fresh(self._restart_path):
                    logger.warning(LOG_STALE_RESTART_FLAG)
                    self._restart_path.unlink(missing_ok=True)
                else:
                    self._restart_path.unlink(missing_ok=True)
                    self.restart_requested = True
                    logger.info(LOG_APP_RESTARTING)
                    self._stop_event.set()
                    return
            self._stop_event.wait(timeout=5)


def main() -> None:
    """Start the application with file-based restart support.

    A background thread polls for ``restart.flag`` every 5 seconds.
    When the file is detected it is deleted and the application restarts
    with freshly loaded plugins, settings, and agent.

    SIGINT / SIGTERM cause a clean exit (no restart).
    """
    setup_logging()

    pid_lock = PidLock(Path(PID_LOCK_FILE))
    try:
        pid_lock.acquire()
    except PidLockError as exc:
        logger.error(str(exc))
        sys.exit(1)
    atexit.register(pid_lock.release)

    restart_flag = Path(RESTART_FLAG_FILE)
    shutdown_flag = Path(SHUTDOWN_FLAG_FILE)

    try:
        _run_loop(restart_flag, shutdown_flag)
    finally:
        pid_lock.release()


def _run_loop(restart_flag: Path, shutdown_flag: Path) -> None:
    """Run the main restart loop."""
    while True:
        app = Application()
        stop_event = threading.Event()
        watcher = _FlagWatcher(restart_flag, shutdown_flag, stop_event)

        signal.signal(signal.SIGINT, lambda *_, ev=stop_event: ev.set())
        signal.signal(signal.SIGTERM, lambda *_, ev=stop_event: ev.set())

        watcher_thread = threading.Thread(target=watcher.watch, daemon=True)

        try:
            app.start()
            watcher_thread.start()
            stop_event.wait()
        finally:
            app.shutdown()

        if not watcher.restart_requested:
            break


if __name__ == "__main__":
    main()

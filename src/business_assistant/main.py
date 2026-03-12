"""Entry point for the business assistant."""

from __future__ import annotations

import logging
import signal
import threading
from pathlib import Path

from business_assistant.bot.app import Application
from business_assistant.config.constants import (
    LOG_APP_RESTARTING,
    LOG_APP_SHUTDOWN_FLAG,
    RESTART_FLAG_FILE,
    SHUTDOWN_FLAG_FILE,
)
from business_assistant.config.log_setup import setup_logging

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
        self.restart_requested = False

    def watch(self) -> None:
        """Poll every 5 seconds for flag files."""
        while not self._stop_event.is_set():
            if self._shutdown_path.exists():
                self._shutdown_path.unlink(missing_ok=True)
                self.restart_requested = False
                logger.info(LOG_APP_SHUTDOWN_FLAG)
                self._stop_event.set()
                return
            if self._restart_path.exists():
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

    restart_flag = Path(RESTART_FLAG_FILE)
    shutdown_flag = Path(SHUTDOWN_FLAG_FILE)

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

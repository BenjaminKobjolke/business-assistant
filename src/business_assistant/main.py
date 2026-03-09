"""Entry point for the business assistant."""

from __future__ import annotations

import logging
import signal
import threading
from pathlib import Path

from business_assistant.bot.app import Application
from business_assistant.config.constants import LOG_APP_RESTARTING, RESTART_FLAG_FILE

logger = logging.getLogger(__name__)


class _RestartWatcher:
    """Polls for a restart flag file and signals the stop event when found."""

    def __init__(self, flag_path: Path, stop_event: threading.Event) -> None:
        self._flag_path = flag_path
        self._stop_event = stop_event
        self.restart_requested = False

    def watch(self) -> None:
        """Poll every 5 seconds for the restart flag file."""
        while not self._stop_event.is_set():
            if self._flag_path.exists():
                self._flag_path.unlink(missing_ok=True)
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
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    restart_flag = Path(RESTART_FLAG_FILE)

    while True:
        app = Application()
        stop_event = threading.Event()
        watcher = _RestartWatcher(restart_flag, stop_event)

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

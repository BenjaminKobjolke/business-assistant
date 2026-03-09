"""Entry point for the business assistant."""

from __future__ import annotations

import logging
import signal
import threading

from business_assistant.bot.app import Application


def main() -> None:
    """Start the application and block until interrupted."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    app = Application()
    stop_event = threading.Event()

    def _signal_handler(signum: int, frame: object) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    try:
        app.start()
        stop_event.wait()
    finally:
        app.shutdown()


if __name__ == "__main__":
    main()

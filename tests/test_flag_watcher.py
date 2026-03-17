"""Tests for the _FlagWatcher stale-flag protection."""

from __future__ import annotations

import os
import threading
from pathlib import Path

from business_assistant.main import _FlagWatcher


def _set_mtime(path: Path, mtime: float) -> None:
    """Set the modification time of *path*."""
    os.utime(path, (mtime, mtime))


class TestStaleFlags:
    """Stale flag files (created before the watcher) must be ignored."""

    def test_stale_restart_flag_ignored(self, tmp_path: Path) -> None:
        restart = tmp_path / "restart.flag"
        shutdown = tmp_path / "shutdown.flag"
        stop = threading.Event()

        watcher = _FlagWatcher(restart, shutdown, stop)

        # Create flag with mtime in the past (before watcher start)
        restart.touch()
        _set_mtime(restart, watcher._start_time - 10)

        # Run one poll cycle then stop
        stop_after = threading.Timer(0.3, stop.set)
        stop_after.start()
        watcher.watch()

        assert not watcher.restart_requested
        assert not restart.exists(), "stale flag should be deleted"

    def test_stale_shutdown_flag_ignored(self, tmp_path: Path) -> None:
        restart = tmp_path / "restart.flag"
        shutdown = tmp_path / "shutdown.flag"
        stop = threading.Event()

        watcher = _FlagWatcher(restart, shutdown, stop)

        shutdown.touch()
        _set_mtime(shutdown, watcher._start_time - 10)

        stop_after = threading.Timer(0.3, stop.set)
        stop_after.start()
        watcher.watch()

        assert not watcher.restart_requested
        assert not shutdown.exists(), "stale flag should be deleted"


class TestFreshFlags:
    """Fresh flag files (created after the watcher) must be honored."""

    def test_fresh_restart_flag_honored(self, tmp_path: Path) -> None:
        restart = tmp_path / "restart.flag"
        shutdown = tmp_path / "shutdown.flag"
        stop = threading.Event()

        watcher = _FlagWatcher(restart, shutdown, stop)

        # Create flag with mtime in the future (after watcher start)
        restart.touch()
        _set_mtime(restart, watcher._start_time + 10)

        watcher.watch()

        assert watcher.restart_requested is True
        assert not restart.exists(), "flag should be deleted after honoring"
        assert stop.is_set()

    def test_fresh_shutdown_flag_honored(self, tmp_path: Path) -> None:
        restart = tmp_path / "restart.flag"
        shutdown = tmp_path / "shutdown.flag"
        stop = threading.Event()

        watcher = _FlagWatcher(restart, shutdown, stop)

        shutdown.touch()
        _set_mtime(shutdown, watcher._start_time + 10)

        watcher.watch()

        assert watcher.restart_requested is False
        assert not shutdown.exists()
        assert stop.is_set()

    def test_shutdown_checked_before_restart(self, tmp_path: Path) -> None:
        """When both flags are fresh, shutdown takes priority."""
        restart = tmp_path / "restart.flag"
        shutdown = tmp_path / "shutdown.flag"
        stop = threading.Event()

        watcher = _FlagWatcher(restart, shutdown, stop)

        future = watcher._start_time + 10
        restart.touch()
        _set_mtime(restart, future)
        shutdown.touch()
        _set_mtime(shutdown, future)

        watcher.watch()

        assert watcher.restart_requested is False, "shutdown should win over restart"
        assert not shutdown.exists()
        assert stop.is_set()

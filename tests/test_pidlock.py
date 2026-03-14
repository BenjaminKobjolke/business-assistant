"""Tests for PID lock single-instance guard."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from business_assistant.config.pidlock import PidLock, PidLockError


class TestPidLock:
    def test_acquire_creates_pid_file(self, tmp_path: Path) -> None:
        pid_file = tmp_path / "bot.pid"
        lock = PidLock(pid_file)

        lock.acquire()

        assert pid_file.exists()
        assert pid_file.read_text() == str(os.getpid())

    def test_release_deletes_pid_file(self, tmp_path: Path) -> None:
        pid_file = tmp_path / "bot.pid"
        lock = PidLock(pid_file)
        lock.acquire()

        lock.release()

        assert not pid_file.exists()

    def test_release_idempotent(self, tmp_path: Path) -> None:
        pid_file = tmp_path / "bot.pid"
        lock = PidLock(pid_file)
        lock.acquire()

        lock.release()
        lock.release()  # should not raise

    def test_acquire_stale_pid_overwrites(self, tmp_path: Path) -> None:
        pid_file = tmp_path / "bot.pid"
        pid_file.write_text("99999999")  # PID unlikely to exist
        lock = PidLock(pid_file)

        with patch(
            "business_assistant.config.pidlock._is_process_alive", return_value=False
        ):
            lock.acquire()

        assert pid_file.read_text() == str(os.getpid())

    def test_acquire_live_pid_shuts_down(self, tmp_path: Path) -> None:
        pid_file = tmp_path / "bot.pid"
        pid_file.write_text("12345")
        lock = PidLock(pid_file)

        # Simulate: alive on first check, then dead after shutdown.flag is created
        alive_calls = iter([True, True, False, False])

        with (
            patch(
                "business_assistant.config.pidlock._is_process_alive",
                side_effect=lambda pid: next(alive_calls),
            ),
            patch(
                "business_assistant.config.pidlock.Path.touch"
            ) as mock_touch,
            patch("business_assistant.config.pidlock.time.sleep"),
        ):
            lock.acquire()

        mock_touch.assert_called_once()
        assert pid_file.read_text() == str(os.getpid())

    def test_acquire_timeout_raises(self, tmp_path: Path) -> None:
        pid_file = tmp_path / "bot.pid"
        pid_file.write_text("12345")
        lock = PidLock(pid_file)

        with (
            patch(
                "business_assistant.config.pidlock._is_process_alive",
                return_value=True,
            ),
            patch("business_assistant.config.pidlock.time.sleep"),
            pytest.raises(PidLockError, match="did not stop"),
        ):
            lock.acquire(timeout=3)

    def test_acquire_corrupt_pid_file(self, tmp_path: Path) -> None:
        pid_file = tmp_path / "bot.pid"
        pid_file.write_text("not-a-number")
        lock = PidLock(pid_file)

        lock.acquire()

        assert pid_file.read_text() == str(os.getpid())

    def test_acquire_empty_pid_file(self, tmp_path: Path) -> None:
        pid_file = tmp_path / "bot.pid"
        pid_file.write_text("")
        lock = PidLock(pid_file)

        lock.acquire()

        assert pid_file.read_text() == str(os.getpid())

    def test_is_process_alive_current_process(self) -> None:
        from business_assistant.config.pidlock import _is_process_alive

        assert _is_process_alive(os.getpid()) is True

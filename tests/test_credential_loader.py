"""Tests for credential file loading."""

from __future__ import annotations

import os
from pathlib import Path

from business_assistant.bot.app import _load_credential_files
from business_assistant.config.constants import ENV_RTM_TOKEN


class TestLoadCredentialFiles:
    def test_sets_env_from_file(self, tmp_path: Path, monkeypatch) -> None:
        """Token file exists and env var is unset — should set env var."""
        monkeypatch.delenv(ENV_RTM_TOKEN, raising=False)

        cred_dir = tmp_path / "data"
        cred_dir.mkdir()
        (cred_dir / "rtm_token").write_text("my-secret-token", encoding="utf-8")

        _load_credential_files(project_root=tmp_path)

        assert os.environ[ENV_RTM_TOKEN] == "my-secret-token"

    def test_strips_whitespace(self, tmp_path: Path, monkeypatch) -> None:
        """Token file with trailing newline — should be stripped."""
        monkeypatch.delenv(ENV_RTM_TOKEN, raising=False)

        cred_dir = tmp_path / "data"
        cred_dir.mkdir()
        (cred_dir / "rtm_token").write_text("  abc123\n", encoding="utf-8")

        _load_credential_files(project_root=tmp_path)

        assert os.environ[ENV_RTM_TOKEN] == "abc123"

    def test_skips_when_env_already_set(self, tmp_path: Path, monkeypatch) -> None:
        """Env var already set — file should not override it."""
        monkeypatch.setenv(ENV_RTM_TOKEN, "existing-token")

        cred_dir = tmp_path / "data"
        cred_dir.mkdir()
        (cred_dir / "rtm_token").write_text("file-token", encoding="utf-8")

        _load_credential_files(project_root=tmp_path)

        assert os.environ[ENV_RTM_TOKEN] == "existing-token"

    def test_skips_missing_file(self, tmp_path: Path, monkeypatch) -> None:
        """No file — env var should remain unset."""
        monkeypatch.delenv(ENV_RTM_TOKEN, raising=False)

        _load_credential_files(project_root=tmp_path)

        assert os.environ.get(ENV_RTM_TOKEN) is None

    def test_skips_empty_file(self, tmp_path: Path, monkeypatch) -> None:
        """Empty file — env var should remain unset."""
        monkeypatch.delenv(ENV_RTM_TOKEN, raising=False)

        cred_dir = tmp_path / "data"
        cred_dir.mkdir()
        (cred_dir / "rtm_token").write_text("", encoding="utf-8")

        _load_credential_files(project_root=tmp_path)

        assert os.environ.get(ENV_RTM_TOKEN) is None

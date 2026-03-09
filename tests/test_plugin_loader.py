"""Tests for dynamic plugin loading."""

from __future__ import annotations

import types
from unittest.mock import MagicMock

from business_assistant.plugins.loader import load_plugins
from business_assistant.plugins.registry import PluginRegistry


class TestPluginLoader:
    def test_load_valid_plugin(self, monkeypatch) -> None:
        mock_module = types.ModuleType("fake_plugin")
        mock_module.register = MagicMock()

        monkeypatch.setattr(
            "business_assistant.plugins.loader.importlib.import_module",
            lambda name: mock_module,
        )

        registry = PluginRegistry()
        load_plugins(registry, ["fake_plugin"])

        mock_module.register.assert_called_once_with(registry)

    def test_load_missing_plugin(self, monkeypatch) -> None:
        def fail_import(name: str) -> None:
            raise ImportError(f"No module named '{name}'")

        monkeypatch.setattr(
            "business_assistant.plugins.loader.importlib.import_module",
            fail_import,
        )

        registry = PluginRegistry()
        load_plugins(registry, ["nonexistent_plugin"])
        assert registry.all_tools() == []

    def test_skip_empty_names(self, monkeypatch) -> None:
        call_count = 0

        def counting_import(name: str) -> types.ModuleType:
            nonlocal call_count
            call_count += 1
            mod = types.ModuleType(name)
            mod.register = MagicMock()
            return mod

        monkeypatch.setattr(
            "business_assistant.plugins.loader.importlib.import_module",
            counting_import,
        )

        registry = PluginRegistry()
        load_plugins(registry, ["", "  ", "valid_plugin"])
        assert call_count == 1

    def test_plugin_register_error(self, monkeypatch) -> None:
        mock_module = types.ModuleType("bad_plugin")
        mock_module.register = MagicMock(side_effect=RuntimeError("oops"))

        monkeypatch.setattr(
            "business_assistant.plugins.loader.importlib.import_module",
            lambda name: mock_module,
        )

        registry = PluginRegistry()
        load_plugins(registry, ["bad_plugin"])
        assert registry.all_tools() == []

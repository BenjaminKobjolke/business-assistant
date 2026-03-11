"""Tests for dynamic plugin loading."""

from __future__ import annotations

import logging
import types
from unittest.mock import MagicMock

from business_assistant.plugins.loader import load_plugins
from business_assistant.plugins.registry import (
    PluginInfo,
    PluginRegistry,
)


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


class TestPluginLoaderCategoryValidation:
    def test_load_plugins_logs_unmet_requirements(self, monkeypatch, caplog) -> None:
        def fake_import(name: str) -> types.ModuleType:
            mod = types.ModuleType(name)

            def register(registry: PluginRegistry) -> None:
                registry.register(
                    PluginInfo(
                        name="needy",
                        description="Needs todo",
                        required_categories=("todo",),
                    ),
                    [],
                )

            mod.register = register
            return mod

        monkeypatch.setattr(
            "business_assistant.plugins.loader.importlib.import_module",
            fake_import,
        )

        registry = PluginRegistry()
        with caplog.at_level(logging.WARNING):
            load_plugins(registry, ["needy_plugin"])

        assert any("todo" in r.message for r in caplog.records)

    def test_load_plugins_no_warning_when_satisfied(self, monkeypatch, caplog) -> None:
        call_order: list[str] = []

        def fake_import(name: str) -> types.ModuleType:
            mod = types.ModuleType(name)
            if name == "provider":

                def register(registry: PluginRegistry) -> None:
                    call_order.append("provider")
                    registry.register(
                        PluginInfo(name="rtm", description="RTM", category="todo"),
                        [],
                    )

                mod.register = register
            else:

                def register(registry: PluginRegistry) -> None:
                    call_order.append("consumer")
                    registry.register(
                        PluginInfo(
                            name="dep",
                            description="Dep",
                            required_categories=("todo",),
                        ),
                        [],
                    )

                mod.register = register
            return mod

        monkeypatch.setattr(
            "business_assistant.plugins.loader.importlib.import_module",
            fake_import,
        )

        registry = PluginRegistry()
        with caplog.at_level(logging.WARNING):
            load_plugins(registry, ["provider", "consumer"])

        warning_messages = [
            r.message for r in caplog.records if r.levelno >= logging.WARNING
        ]
        assert not any("todo" in msg for msg in warning_messages)

    def test_category_conflict_during_load(self, monkeypatch, caplog) -> None:
        call_count = 0

        def fake_import(name: str) -> types.ModuleType:
            nonlocal call_count
            call_count += 1
            mod = types.ModuleType(name)

            def register(registry: PluginRegistry) -> None:
                registry.register(
                    PluginInfo(
                        name=f"todo_{call_count}",
                        description=f"Todo {call_count}",
                        category="todo",
                    ),
                    [],
                )

            mod.register = register
            return mod

        monkeypatch.setattr(
            "business_assistant.plugins.loader.importlib.import_module",
            fake_import,
        )

        registry = PluginRegistry()
        with caplog.at_level(logging.WARNING):
            load_plugins(registry, ["plugin_a", "plugin_b"])

        # First plugin registered successfully
        assert registry.plugin_for_category("todo") is not None
        assert registry.plugin_for_category("todo").name == "todo_1"
        # Second plugin failed (conflict logged as warning)
        assert len(registry.plugins) == 1

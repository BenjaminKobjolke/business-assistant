"""Dynamic plugin loader — imports modules listed in settings and calls register()."""

from __future__ import annotations

import importlib
import logging

from .registry import PluginRegistry

logger = logging.getLogger(__name__)


def load_plugins(registry: PluginRegistry, plugin_names: list[str]) -> None:
    """Import each plugin module and call its register(registry) entry point.

    Args:
        registry: The plugin registry to pass to each plugin.
        plugin_names: List of Python module names to import.
    """
    for name in plugin_names:
        name = name.strip()
        if not name:
            continue
        try:
            module = importlib.import_module(name)
            module.register(registry)
            logger.info("Loaded plugin: %s", name)
        except Exception:
            logger.warning("Failed to load plugin: %s", name, exc_info=True)

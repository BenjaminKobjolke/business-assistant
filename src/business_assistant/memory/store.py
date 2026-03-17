"""JSON-file backed key-value memory store (thread-safe)."""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


class MemoryStore:
    """Thread-safe, JSON-file backed key-value store.

    Keys are case-insensitive and stored in lower case.
    """

    def __init__(self, file_path: str) -> None:
        self._file_path = Path(file_path)
        self._lock = threading.Lock()
        self._data: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        """Load data from disk. Creates empty store if file missing or corrupt."""
        if not self._file_path.exists():
            self._data = {}
            return
        try:
            text = self._file_path.read_text(encoding="utf-8")
            loaded = json.loads(text)
            if isinstance(loaded, dict):
                self._data = {k.lower(): v for k, v in loaded.items()}
            else:
                logger.warning("Memory file contains non-dict data, starting fresh")
                self._data = {}
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load memory file, starting fresh: %s", e)
            self._data = {}

    def _save(self) -> None:
        """Persist data to disk."""
        os.makedirs(self._file_path.parent, exist_ok=True)
        self._file_path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def get(self, key: str, default: str | None = None) -> str | None:
        """Get a value by key (case-insensitive)."""
        with self._lock:
            return self._data.get(key.lower(), default)

    def set(self, key: str, value: str) -> None:
        """Set a key-value pair (case-insensitive key)."""
        with self._lock:
            self._data[key.lower()] = value
            self._save()

    def delete(self, key: str) -> bool:
        """Delete a key. Returns True if the key existed."""
        with self._lock:
            if key.lower() in self._data:
                del self._data[key.lower()]
                self._save()
                return True
            return False

    def list_all(self) -> dict[str, str]:
        """Return a copy of all stored key-value pairs."""
        with self._lock:
            return dict(self._data)

    def search(self, query: str) -> dict[str, str]:
        """Search for keys or values containing the query string (case-insensitive)."""
        q = query.lower()
        with self._lock:
            return {
                k: v
                for k, v in self._data.items()
                if q in k.lower() or q in v.lower()
            }

    def format_contents(self) -> str:
        """Format all memory contents as a readable string for the system prompt."""
        with self._lock:
            if not self._data:
                return "(empty)"
            lines = [f"- {k}: {v}" for k, v in sorted(self._data.items())]
            return "\n".join(lines)

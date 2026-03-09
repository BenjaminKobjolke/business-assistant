"""Tests for MemoryStore."""

from __future__ import annotations

import threading
from pathlib import Path

from business_assistant.memory.store import MemoryStore


class TestMemoryStore:
    def test_set_and_get(self, memory_store: MemoryStore) -> None:
        memory_store.set("Name", "Alice")
        assert memory_store.get("name") == "Alice"
        assert memory_store.get("NAME") == "Alice"

    def test_get_missing_key(self, memory_store: MemoryStore) -> None:
        assert memory_store.get("nonexistent") is None

    def test_delete_existing(self, memory_store: MemoryStore) -> None:
        memory_store.set("key", "value")
        assert memory_store.delete("key") is True
        assert memory_store.get("key") is None

    def test_delete_missing(self, memory_store: MemoryStore) -> None:
        assert memory_store.delete("missing") is False

    def test_list_all(self, memory_store: MemoryStore) -> None:
        memory_store.set("a", "1")
        memory_store.set("b", "2")
        result = memory_store.list_all()
        assert result == {"a": "1", "b": "2"}

    def test_search(self, memory_store: MemoryStore) -> None:
        memory_store.set("markus_email", "markus@example.com")
        memory_store.set("other", "something")
        result = memory_store.search("markus")
        assert "markus_email" in result
        assert "other" not in result

    def test_persistence(self, tmp_memory_file: str) -> None:
        store1 = MemoryStore(tmp_memory_file)
        store1.set("persist", "yes")

        store2 = MemoryStore(tmp_memory_file)
        assert store2.get("persist") == "yes"

    def test_corrupt_file(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text("not json at all", encoding="utf-8")
        store = MemoryStore(str(path))
        assert store.list_all() == {}

    def test_thread_safety(self, memory_store: MemoryStore) -> None:
        errors: list[Exception] = []

        def writer(prefix: str) -> None:
            try:
                for i in range(50):
                    memory_store.set(f"{prefix}_{i}", str(i))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(f"t{n}",)) for n in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(memory_store.list_all()) == 200

    def test_format_contents_empty(self, memory_store: MemoryStore) -> None:
        assert memory_store.format_contents() == "(empty)"

    def test_format_contents(self, memory_store: MemoryStore) -> None:
        memory_store.set("key", "value")
        assert "- key: value" in memory_store.format_contents()

    def test_case_insensitive_keys(self, memory_store: MemoryStore) -> None:
        memory_store.set("MyKey", "first")
        memory_store.set("MYKEY", "second")
        assert memory_store.get("mykey") == "second"
        assert len(memory_store.list_all()) == 1

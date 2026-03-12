"""Read and filter JSONL usage log files."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def read_entries(
    log_dir: str | Path,
    legacy_file: str | Path | None = None,
) -> list[dict]:
    """Read all usage.*.jsonl files from a directory, plus an optional legacy file."""
    entries: list[dict] = []
    log_path = Path(log_dir)

    if log_path.is_dir():
        for f in sorted(log_path.glob("usage.*.jsonl")):
            entries.extend(_read_file(f))

    if legacy_file:
        lf = Path(legacy_file)
        if lf.is_file():
            entries.extend(_read_file(lf))

    return entries


def _read_file(path: Path) -> list[dict]:
    """Read JSONL entries from a single file, skipping malformed lines."""
    results: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning("Skipping malformed line %d in %s", line_no, path)
    return results


def filter_entries(
    entries: list[dict],
    start: datetime,
    end: datetime,
) -> list[dict]:
    """Filter entries where start <= ts < end."""
    filtered: list[dict] = []
    for entry in entries:
        ts_str = entry.get("ts")
        if not ts_str:
            continue
        try:
            ts = datetime.fromisoformat(ts_str)
            if start <= ts < end:
                filtered.append(entry)
        except (ValueError, TypeError):
            continue
    return filtered

"""Fetch and cache model pricing from litellm's public database."""

from __future__ import annotations

import json
import sqlite3
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

LITELLM_PRICES_URL = (
    "https://raw.githubusercontent.com/BerriAI/litellm/main/"
    "model_prices_and_context_window.json"
)

_DEFAULT_DB_PATH = Path("data/price_cache.db")
_CACHE_TTL = timedelta(hours=24)


@dataclass(frozen=True)
class ModelPricing:
    """Per-token costs for a single model."""

    input_cost: float
    output_cost: float
    cache_read_cost: float


def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS models ("
        "  model TEXT PRIMARY KEY,"
        "  input_cost REAL,"
        "  output_cost REAL,"
        "  cache_read_cost REAL,"
        "  fetched_at TEXT"
        ")"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS meta ("
        "  key TEXT PRIMARY KEY,"
        "  value TEXT"
        ")"
    )
    conn.commit()


def _fetch_litellm_prices() -> dict:
    """Download the litellm pricing JSON."""
    req = urllib.request.Request(LITELLM_PRICES_URL)
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def _ensure_fresh(db_path: Path, *, force: bool = False) -> None:
    """Re-fetch prices if the cache is stale or missing."""
    conn = sqlite3.connect(str(db_path))
    try:
        _init_db(conn)

        if not force:
            row = conn.execute(
                "SELECT value FROM meta WHERE key = 'last_fetched'"
            ).fetchone()
            if row:
                last = datetime.fromisoformat(row[0])
                if datetime.now(tz=UTC) - last < _CACHE_TTL:
                    return

        data = _fetch_litellm_prices()
        now_iso = datetime.now(tz=UTC).isoformat()

        for model_name, info in data.items():
            if not isinstance(info, dict):
                continue
            input_cost = info.get("input_cost_per_token", 0.0) or 0.0
            output_cost = info.get("output_cost_per_token", 0.0) or 0.0
            cache_read_cost = info.get("cache_read_input_token_cost", 0.0) or 0.0
            conn.execute(
                "INSERT OR REPLACE INTO models "
                "(model, input_cost, output_cost, cache_read_cost, fetched_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (model_name, input_cost, output_cost, cache_read_cost, now_iso),
            )

        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES ('last_fetched', ?)",
            (now_iso,),
        )
        conn.commit()
    finally:
        conn.close()


def load_prices(
    db_path: Path = _DEFAULT_DB_PATH, *, force: bool = False
) -> dict[str, ModelPricing]:
    """Load all model prices from the SQLite cache, refreshing if needed."""
    _ensure_fresh(db_path, force=force)

    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT model, input_cost, output_cost, cache_read_cost FROM models"
        ).fetchall()
    finally:
        conn.close()

    return {
        row[0]: ModelPricing(
            input_cost=row[1],
            output_cost=row[2],
            cache_read_cost=row[3],
        )
        for row in rows
    }


def compute_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int,
    prices: dict[str, ModelPricing],
) -> float | None:
    """Calculate cost for a single usage entry. Returns None if model not found."""
    pricing = _lookup_model(model, prices)
    if pricing is None:
        return None
    return (
        input_tokens * pricing.input_cost
        + output_tokens * pricing.output_cost
        + cache_read_tokens * pricing.cache_read_cost
    )


def _lookup_model(model: str, prices: dict[str, ModelPricing]) -> ModelPricing | None:
    """Look up model pricing: exact match first, then prefix match."""
    if model in prices:
        return prices[model]
    # Try prefix match (e.g. "gpt-4o" matches "gpt-4o-2025-01-01")
    for name, pricing in prices.items():
        if name.startswith(model):
            return pricing
    # Try if the entry is a prefix of the model name
    for name, pricing in prices.items():
        if model.startswith(name):
            return pricing
    return None

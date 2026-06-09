from __future__ import annotations

import json
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.models.enums import ComfortLevel

_CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "daily_costs_catalog.json"

_COMFORT_KEYS: dict[ComfortLevel | None, str] = {
    ComfortLevel.economy: "economy",
    ComfortLevel.standard: "standard",
    ComfortLevel.comfort: "comfort",
    None: "standard",
}


@lru_cache(maxsize=1)
def _load_raw_catalog() -> dict[str, Any]:
    if not _CATALOG_PATH.exists():
        return {"defaults": {}, "cities": {}}
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


def _pick_tier(values: dict[str, Any], comfort_level: ComfortLevel | None) -> Decimal:
    key = _COMFORT_KEYS[comfort_level]
    raw = values.get(key) or values.get("standard")
    return Decimal(str(raw))


def lookup_daily_costs(
    destination: str,
    comfort_level: ComfortLevel | None,
) -> tuple[Decimal, Decimal, str, str]:
    catalog = _load_raw_catalog()
    defaults = catalog.get("defaults", {})
    city_key = destination.strip().lower()
    entry = catalog.get("cities", {}).get(city_key, defaults)

    food = _pick_tier(entry.get("food_rub_per_day", defaults.get("food_rub_per_day", {})), comfort_level)
    transport = _pick_tier(
        entry.get("transport_rub_per_person_per_day", defaults.get("transport_rub_per_person_per_day", {})),
        comfort_level,
    )
    food_source = entry.get("source_food") or defaults.get("source_food", "Voyago catalog, 2026")
    transport_source = entry.get("source_transport") or defaults.get(
        "source_transport", "Voyago catalog, 2026"
    )
    return food, transport, str(food_source), str(transport_source)


def catalog_metadata() -> dict[str, Any]:
    raw = _load_raw_catalog()
    return raw.get("_meta", {})

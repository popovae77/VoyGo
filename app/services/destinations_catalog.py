"""Справочник направлений и кодов аэропортов (IATA) для перелётов и автодополнения."""

from __future__ import annotations

from app.services.destinations_catalog_entries import DESTINATIONS_ENTRIES

DESTINATIONS: list[dict[str, str]] = DESTINATIONS_ENTRIES


def _normalize_key(text: str) -> str:
    return text.strip().lower().replace("ё", "е")


IATA_BY_VALUE: dict[str, str] = {item["value"]: item["iata"] for item in DESTINATIONS}
IATA_BY_TITLE: dict[str, str] = {_normalize_key(item["title"]): item["iata"] for item in DESTINATIONS}

DEFAULT_ORIGIN_TITLE = "Москва"

ORIGIN_QUICK_TITLES: tuple[str, ...] = (
    "Москва",
    "Санкт-Петербург",
    "Казань",
    "Екатеринбург",
    "Сочи",
    "Калининград",
)


def resolve_place_iata(place: str) -> str | None:
    """Возвращает IATA по slug, названию, алиасу или коду из 3 латинских букв."""
    raw = place.strip()
    if not raw:
        return None

    if len(raw) == 3 and raw.isascii():
        return raw.upper()

    key = _normalize_key(raw)
    direct = IATA_BY_VALUE.get(key) or IATA_BY_TITLE.get(key)
    if direct:
        return direct

    for item in DESTINATIONS:
        if key == _normalize_key(item["title"]) or key == item["value"]:
            return item["iata"]
        alias_tokens = [_normalize_key(part) for part in item.get("aliases", "").split() if part.strip()]
        if key in alias_tokens:
            return item["iata"]

    return None


def city_display_name(place: str) -> str | None:
    """Русское название для отелей/Google, если есть в каталоге."""
    key = _normalize_key(place)
    for item in DESTINATIONS:
        if key in {item["value"], _normalize_key(item["title"])}:
            return item["title"]
        if key in item.get("aliases", "").split():
            return item["title"]
    return None


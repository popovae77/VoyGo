"""Hotellook / Travelpayouts hotel price API (with graceful fallback)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import logging

import httpx

from app.services.hotel_price_types import HotelPriceResult

logger = logging.getLogger(__name__)

HOTELLOOK_LOOKUP_URL = "https://engine.hotellook.com/api/v2/lookup.json"
HOTELLOOK_CACHE_URL = "https://engine.hotellook.com/api/v2/cache.json"
HOTELLOOK_WIDGET_URL = "https://yasen.hotellook.com/tp/public/widget_location_dump.json"

# English location names for Hotellook cache.json (when API is available).
LOCATION_EN: dict[str, str] = {
    "сочи": "Sochi",
    "москва": "Moscow",
    "санкт-петербург": "Saint Petersburg",
    "казань": "Kazan",
    "стамбул": "Istanbul",
    "анталия": "Antalya",
    "дубай": "Dubai",
    "париж": "Paris",
}


class HotellookClient:
    def __init__(self, token: str, timeout: float = 12.0) -> None:
        self.token = token
        self.timeout = timeout

    def resolve_location_en(self, destination: str) -> str | None:
        normalized = destination.strip().lower()
        if normalized in LOCATION_EN:
            return LOCATION_EN[normalized]
        if destination.strip().replace(" ", "").isascii():
            return destination.strip().title()
        return None

    def lookup_city_id(self, destination: str) -> int | None:
        query = self.resolve_location_en(destination) or destination.strip()
        try:
            response = httpx.get(
                HOTELLOOK_LOOKUP_URL,
                params={
                    "query": query,
                    "lang": "ru",
                    "lookFor": "city",
                    "limit": 1,
                    "token": self.token,
                },
                headers={"X-Access-Token": self.token},
                timeout=self.timeout,
                follow_redirects=True,
            )
            if response.status_code != 200:
                return None
            payload = response.json()
            locations = payload.get("results", {}).get("locations", [])
            if not locations:
                return None
            location_id = locations[0].get("id")
            return int(location_id) if location_id is not None else None
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            logger.debug("Hotellook lookup failed: %s", exc)
            return None

    def fetch_min_price_per_night(
        self,
        destination: str,
        check_in: date,
        check_out: date,
    ) -> HotelPriceResult | None:
        nights = (check_out - check_in).days
        if nights <= 0:
            return None

        location_en = self.resolve_location_en(destination)
        if not location_en:
            return None

        total = self._fetch_cache_total(location_en, check_in, check_out)
        if total is None:
            location_id = self.lookup_city_id(destination)
            if location_id is not None:
                total = self._fetch_widget_total(location_id, check_in, check_out)

        if total is None or total <= 0:
            return None

        per_night = (total / Decimal(nights)).quantize(Decimal("0.01"))
        return HotelPriceResult(
            price_per_night=per_night,
            source="Hotellook / Travelpayouts",
            location_id=self.lookup_city_id(destination),
        )

    def _fetch_cache_total(self, location_en: str, check_in: date, check_out: date) -> Decimal | None:
        params = {
            "location": location_en,
            "checkIn": check_in.isoformat(),
            "checkOut": check_out.isoformat(),
            "currency": "rub",
            "limit": 8,
            "token": self.token,
        }
        try:
            response = httpx.get(
                HOTELLOOK_CACHE_URL,
                params=params,
                headers={"X-Access-Token": self.token},
                timeout=self.timeout,
                follow_redirects=True,
            )
            if response.status_code != 200:
                return None
            payload = response.json()
            return self._extract_total_price(payload)
        except (httpx.HTTPError, ValueError) as exc:
            logger.debug("Hotellook cache failed: %s", exc)
            return None

    def _fetch_widget_total(self, location_id: int, check_in: date, check_out: date) -> Decimal | None:
        params = {
            "currency": "rub",
            "language": "ru",
            "limit": 8,
            "id": location_id,
            "type": "popularity",
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "token": self.token,
        }
        try:
            response = httpx.get(
                HOTELLOOK_WIDGET_URL,
                params=params,
                headers={"X-Access-Token": self.token},
                timeout=self.timeout,
                follow_redirects=True,
            )
            if response.status_code != 200:
                return None
            payload = response.json()
            hotels = payload.get("hotels", []) if isinstance(payload, dict) else []
            prices: list[Decimal] = []
            for hotel in hotels:
                if not isinstance(hotel, dict):
                    continue
                for key in ("priceFrom", "price", "minRate", "rate"):
                    if hotel.get(key) is not None:
                        prices.append(Decimal(str(hotel[key])))
                        break
            if not prices:
                return None
            return min(prices).quantize(Decimal("0.01"))
        except (httpx.HTTPError, ValueError) as exc:
            logger.debug("Hotellook widget failed: %s", exc)
            return None

    @staticmethod
    def _extract_total_price(payload: object) -> Decimal | None:
        if isinstance(payload, dict):
            for key in ("priceFrom", "priceAvg", "minPrice", "price"):
                if payload.get(key) is not None:
                    return Decimal(str(payload[key])).quantize(Decimal("0.01"))
            percentiles = payload.get("pricePercentile") or payload.get("price_percentile")
            if isinstance(percentiles, dict):
                for key in ("50", "35", "10"):
                    if percentiles.get(key) is not None:
                        return Decimal(str(percentiles[key])).quantize(Decimal("0.01"))
        if isinstance(payload, list):
            prices: list[Decimal] = []
            for item in payload:
                value = HotellookClient._extract_total_price(item)
                if value is not None:
                    prices.append(value)
            if prices:
                return min(prices)
        return None

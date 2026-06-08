"""SerpApi Google Hotels — real prices with check-in/out dates."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import logging
from urllib.parse import quote

import httpx

from app.services.hotel_price_types import HotelPriceResult

logger = logging.getLogger(__name__)

SERPAPI_SEARCH_URL = "https://serpapi.com/search"

from app.services.destinations_catalog import DESTINATIONS

CITY_QUERY: dict[str, str] = {item["value"]: item["title"] for item in DESTINATIONS}


class SerpApiHotelsClient:
    def __init__(self, api_key: str, timeout: float = 30.0) -> None:
        self.api_key = api_key
        self.timeout = timeout

    def resolve_query_city(self, destination: str) -> str:
        normalized = destination.strip().lower()
        if normalized in CITY_QUERY:
            return CITY_QUERY[normalized]
        return destination.strip()

    def fetch_min_price_per_night(
        self,
        destination: str,
        check_in: date,
        check_out: date,
        adults: int = 2,
    ) -> HotelPriceResult | None:
        nights = (check_out - check_in).days
        if nights <= 0:
            return None
        city = self.resolve_query_city(destination)
        params = {
            "engine": "google_hotels",
            "q": f"отели {city}",
            "check_in_date": check_in.isoformat(),
            "check_out_date": check_out.isoformat(),
            "adults": max(adults, 1),
            "currency": "RUB",
            "hl": "ru",
            "gl": "ru",
            "sort_by": "3",
            "api_key": self.api_key,
        }
        try:
            response = httpx.get(SERPAPI_SEARCH_URL, params=params, timeout=self.timeout)
            if response.status_code != 200:
                logger.debug("SerpApi hotels HTTP %s: %s", response.status_code, response.text[:200])
                return None
            payload = response.json()
            if payload.get("error"):
                logger.debug("SerpApi error: %s", payload.get("error"))
                return None
            picked = self._pick_best_property(payload)
            if picked is None:
                return None
            per_night, hotel_name, booking_url = picked
            return HotelPriceResult(
                price_per_night=per_night,
                source="Google Hotels / SerpApi",
                hotel_name=hotel_name,
                booking_url=booking_url,
            )
        except (httpx.HTTPError, ValueError) as exc:
            logger.debug("SerpApi hotels failed: %s", exc)
            return None

    @staticmethod
    def _property_price(item: dict) -> Decimal | None:
        if item.get("extracted_price") is not None:
            return Decimal(str(item["extracted_price"])).quantize(Decimal("0.01"))
        rate = item.get("rate_per_night")
        if isinstance(rate, dict) and rate.get("extracted_lowest") is not None:
            return Decimal(str(rate["extracted_lowest"])).quantize(Decimal("0.01"))
        total = item.get("total_rate")
        if isinstance(total, dict) and total.get("extracted_lowest") is not None:
            return Decimal(str(total["extracted_lowest"])).quantize(Decimal("0.01"))
        return None

    @classmethod
    def _pick_best_property(cls, payload: dict) -> tuple[Decimal, str, str] | None:
        best: tuple[Decimal, str, str] | None = None
        for key in ("properties", "featured_hotels"):
            items = payload.get(key)
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                price = cls._property_price(item)
                if price is None:
                    continue
                name = str(item.get("name") or "Отель")
                url = (
                    item.get("link")
                    or item.get("serpapi_property_details_link")
                    or item.get("google_hotels_link")
                )
                if not url and item.get("property_token"):
                    url = (
                        "https://serpapi.com/search.json?engine=google_hotels&property_token="
                        + quote(str(item["property_token"]), safe="")
                    )
                if best is None or price < best[0]:
                    best = (price, name, str(url) if url else "")
        if best is None:
            return None
        return best[0], best[1], best[2]

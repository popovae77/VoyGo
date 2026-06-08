"""Makcorps Free Hotel API — real vendor prices (Booking, Priceline, etc.)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import logging
import time

import httpx

from app.services.hotel_price_types import HotelPriceResult

logger = logging.getLogger(__name__)

MAKCORPS_AUTH_URL = "https://api.makcorps.com/auth"
MAKCORPS_FREE_URL = "https://api.makcorps.com/free"

# Slug for /free/{city} — English, lowercase (see https://docs.hotelapi.co/free-hotel-api).
CITY_SLUG: dict[str, str] = {
    "сочи": "sochi",
    "москва": "moscow",
    "санкт-петербург": "saint-petersburg",
    "казань": "kazan",
    "стамбул": "istanbul",
    "анталия": "antalya",
    "дубай": "dubai",
    "париж": "paris",
    "лондон": "london",
    "рим": "rome",
    "барселона": "barcelona",
    "прага": "prague",
    "тбилиси": "tbilisi",
    "ереван": "yerevan",
}


class MakcorpsClient:
    def __init__(
        self,
        username: str,
        password: str,
        *,
        jwt_token: str | None = None,
        usd_to_rub: Decimal = Decimal("95"),
        timeout: float = 25.0,
    ) -> None:
        self.username = username
        self.password = password
        self._jwt = jwt_token
        self._jwt_expires_at = 0.0
        self.usd_to_rub = usd_to_rub
        self.timeout = timeout

    def resolve_city_slug(self, destination: str) -> str | None:
        normalized = destination.strip().lower()
        if normalized in CITY_SLUG:
            return CITY_SLUG[normalized]
        ascii_name = destination.strip().lower().replace(" ", "-")
        if ascii_name.isascii():
            return ascii_name
        return None

    def _ensure_jwt(self) -> str | None:
        if self._jwt and time.time() < self._jwt_expires_at - 120:
            return self._jwt
        if not self.username or not self.password:
            return self._jwt
        try:
            response = httpx.post(
                MAKCORPS_AUTH_URL,
                json={"username": self.username, "password": self.password},
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            token = payload.get("access_token")
            if not token:
                return None
            self._jwt = token
            self._jwt_expires_at = time.time() + 20 * 60
            return self._jwt
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Makcorps auth failed: %s", exc)
            return None

    def fetch_min_price_per_night(
        self,
        destination: str,
        check_in: date,
        check_out: date,
    ) -> HotelPriceResult | None:
        del check_in, check_out  # free tier: random future dates only
        slug = self.resolve_city_slug(destination)
        if not slug:
            return None
        jwt = self._ensure_jwt()
        if not jwt:
            return None
        try:
            response = httpx.get(
                f"{MAKCORPS_FREE_URL}/{slug}",
                headers={"Authorization": f"JWT {jwt}"},
                timeout=self.timeout,
            )
            if response.status_code != 200:
                logger.debug("Makcorps free %s: HTTP %s", slug, response.status_code)
                return None
            min_price = self._min_vendor_price(response.json())
            if min_price is None:
                return None
            rub = (min_price * self.usd_to_rub).quantize(Decimal("0.01"))
            return HotelPriceResult(
                price_per_night=rub,
                source="Makcorps Hotel API (Booking, Priceline…, ориентир USD→RUB)",
            )
        except (httpx.HTTPError, ValueError) as exc:
            logger.debug("Makcorps fetch failed: %s", exc)
            return None

    @staticmethod
    def _min_vendor_price(payload: object) -> Decimal | None:
        if not isinstance(payload, list):
            return None
        prices: list[Decimal] = []
        index = 0
        while index < len(payload):
            block = payload[index]
            index += 1
            if not isinstance(block, list):
                continue
            for vendor in block:
                if not isinstance(vendor, dict):
                    continue
                for key, value in vendor.items():
                    if not key.startswith("price") or value is None:
                        continue
                    try:
                        prices.append(Decimal(str(value)))
                    except Exception:
                        continue
        if not prices:
            return None
        return min(prices)

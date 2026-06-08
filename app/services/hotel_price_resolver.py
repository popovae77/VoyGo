"""Resolve hotel nightly rate: SerpApi → Makcorps → Hotellook → catalog."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.core.config import get_settings
from app.services.hotel_price_types import HotelPriceResult
from app.services.hotellook_client import HotellookClient
from app.services.makcorps_client import MakcorpsClient
from app.services.serpapi_hotels_client import SerpApiHotelsClient


class HotelPriceResolver:
    def __init__(self) -> None:
        settings = get_settings()
        self._serpapi: SerpApiHotelsClient | None = None
        if settings.serpapi_api_key:
            self._serpapi = SerpApiHotelsClient(settings.serpapi_api_key)

        self._makcorps: MakcorpsClient | None = None
        if settings.makcorps_jwt or (settings.makcorps_username and settings.makcorps_password):
            self._makcorps = MakcorpsClient(
                username=settings.makcorps_username or "",
                password=settings.makcorps_password or "",
                jwt_token=settings.makcorps_jwt,
                usd_to_rub=Decimal(str(settings.makcorps_usd_to_rub)),
            )

        self._hotellook: HotellookClient | None = None
        if settings.travelpayouts_token:
            self._hotellook = HotellookClient(settings.travelpayouts_token)

    def fetch(
        self,
        destination: str,
        check_in: date,
        check_out: date,
        adults: int = 2,
    ) -> HotelPriceResult | None:
        if check_out <= check_in:
            return None

        if self._serpapi is not None:
            result = self._serpapi.fetch_min_price_per_night(
                destination, check_in, check_out, adults=adults
            )
            if result is not None:
                return result

        if self._makcorps is not None:
            result = self._makcorps.fetch_min_price_per_night(destination, check_in, check_out)
            if result is not None:
                return result

        if self._hotellook is not None:
            return self._hotellook.fetch_min_price_per_night(destination, check_in, check_out)

        return None

    @staticmethod
    def is_live_source(source: str) -> bool:
        live_prefixes = (
            "Google Hotels / SerpApi",
            "Makcorps Hotel API",
            "Hotellook",
        )
        return any(source.startswith(prefix) for prefix in live_prefixes)

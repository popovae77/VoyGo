from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import json
from pathlib import Path
from typing import Protocol

import httpx

from app.core.config import get_settings
from app.models.enums import ComfortLevel, TravelType
from app.services.daily_costs_catalog import lookup_daily_costs
from app.services.flight_estimates import base_roundtrip_rub
from app.services.hotel_price_resolver import HotelPriceResolver
from app.services.booking_links import build_flight_link, resolve_aviasales_ticket_link
from app.services.iata_codes import resolve_iata, resolve_origin_iata


@dataclass(frozen=True)
class PriceQuote:
    flight_per_person: Decimal
    hotel_per_night: Decimal
    daily_food_per_person: Decimal
    daily_transport_per_person: Decimal
    base_activities: Decimal
    source: str = "mock"
    flight_source: str = "mock"
    accommodation_source: str = "mock"
    food_source: str = "mock"
    transport_source: str = "mock"
    flight_airline: str | None = None
    flight_booking_url: str | None = None
    flight_link_is_specific: bool = False
    hotel_name: str | None = None
    hotel_booking_url: str | None = None
    hotel_link_is_specific: bool = False


class PricingProvider(Protocol):
    def get_quote(
        self,
        destination: str,
        people_count: int,
        travel_type: TravelType,
        comfort_level: ComfortLevel | None,
        start_date: date | None = None,
        end_date: date | None = None,
        origin: str | None = None,
    ) -> PriceQuote:
        ...


_CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "hotel_rates_catalog.json"


def _load_hotel_catalog() -> dict[str, Decimal]:
    if not _CATALOG_PATH.exists():
        return {}
    raw = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    result: dict[str, Decimal] = {}
    for city, info in raw.items():
        if isinstance(info, dict) and info.get("standard") is not None:
            result[city.strip().lower()] = Decimal(str(info["standard"]))
    return result


HOTEL_CATALOG_RATES: dict[str, Decimal] = _load_hotel_catalog()


def comfort_multiplier(comfort_level: ComfortLevel | None) -> Decimal:
    return {
        ComfortLevel.economy: Decimal("0.78"),
        ComfortLevel.standard: Decimal("1.00"),
        ComfortLevel.comfort: Decimal("1.35"),
        None: Decimal("1.00"),
    }[comfort_level]


class MockPricingProvider:
    def __init__(self, discount_factor: Decimal = Decimal("1.00")) -> None:
        self.discount_factor = discount_factor

    def get_quote(
        self,
        destination: str,
        people_count: int,
        travel_type: TravelType,
        comfort_level: ComfortLevel | None,
        start_date: date | None = None,
        end_date: date | None = None,
        origin: str | None = None,
    ) -> PriceQuote:
        destination_factor = self._destination_factor(destination)
        comfort_factor = comfort_multiplier(comfort_level)
        flight_per_person = self.estimate_flight_per_person(
            origin,
            destination,
            travel_type=travel_type,
        )

        multiplier = destination_factor * comfort_factor * self.discount_factor
        hotel_nightly = self._catalog_hotel_rate(destination, comfort_level) or self._money(
            Decimal("4300") * multiplier
        )
        accommodation_source = (
            "Voyago catalog (средние цены по направлению)"
            if self._catalog_hotel_rate(destination, comfort_level) is not None
            else "mock"
        )
        daily_food, daily_transport, food_source, transport_source = lookup_daily_costs(
            destination, comfort_level
        )
        daily_food = self._money(daily_food * self.discount_factor)
        daily_transport = self._money(daily_transport * self.discount_factor)
        return PriceQuote(
            flight_per_person=self._money(flight_per_person * self.discount_factor),
            hotel_per_night=hotel_nightly,
            daily_food_per_person=daily_food,
            daily_transport_per_person=daily_transport,
            base_activities=self._money(Decimal("5200") * destination_factor * self.discount_factor),
            source="catalog-daily-costs" if accommodation_source == "mock" else "catalog-hotels+daily-costs",
            flight_source="ориентировочно (оценка по маршруту)",
            accommodation_source=accommodation_source,
            food_source=food_source,
            transport_source=transport_source,
        )

    @staticmethod
    def _catalog_hotel_rate(destination: str, comfort_level: ComfortLevel | None) -> Decimal | None:
        base = HOTEL_CATALOG_RATES.get(destination.strip().lower())
        if base is None:
            return None
        return (base * comfort_multiplier(comfort_level)).quantize(Decimal("0.01"))

    @staticmethod
    def _destination_factor(destination: str) -> Decimal:
        normalized = destination.strip().lower()
        factors = {
            "сочи": Decimal("0.90"),
            "казань": Decimal("0.82"),
            "санкт-петербург": Decimal("0.95"),
            "стамбул": Decimal("1.15"),
            "анталия": Decimal("1.20"),
            "дубай": Decimal("1.70"),
            "париж": Decimal("1.85"),
            "испания": Decimal("1.55"),
            "барселона": Decimal("1.60"),
            "мадрид": Decimal("1.55"),
            "италия": Decimal("1.65"),
            "рим": Decimal("1.70"),
            "таиланд": Decimal("1.35"),
            "пхукет": Decimal("1.40"),
            "бали": Decimal("1.45"),
            "египет": Decimal("1.25"),
            "сингапур": Decimal("1.55"),
            "япония": Decimal("1.60"),
            "токио": Decimal("1.60"),
            "вьетнам": Decimal("1.30"),
            "малайзия": Decimal("1.35"),
            "хорватия": Decimal("1.25"),
            "аланья": Decimal("1.18"),
            "занзибар": Decimal("1.50"),
            "куба": Decimal("1.45"),
            "доминикана": Decimal("1.42"),
        }
        return factors.get(normalized, Decimal("1.00"))

    @staticmethod
    def estimate_flight_per_person(
        origin: str | None,
        destination: str,
        *,
        travel_type: TravelType = TravelType.beach,
    ) -> Decimal:
        origin_iata = resolve_origin_iata(origin)
        dest_iata = resolve_iata(destination)
        base = base_roundtrip_rub(dest_iata)
        route_factor = MockPricingProvider._route_flight_factor(origin, destination)
        type_flight_factor = Decimal("1.12") if travel_type == TravelType.cruise else Decimal("1.00")
        return MockPricingProvider._money(base * route_factor * type_flight_factor)

    @staticmethod
    def _route_flight_factor(origin: str | None, destination: str) -> Decimal:
        origin_iata = resolve_origin_iata(origin)
        dest_iata = resolve_iata(destination)
        if dest_iata is None:
            return Decimal("1.00")
        route = (origin_iata, dest_iata)
        modifiers: dict[tuple[str, str], Decimal] = {
            ("MOW", "AER"): Decimal("0.90"),
            ("MOW", "LED"): Decimal("0.82"),
            ("MOW", "KZN"): Decimal("0.88"),
            ("MOW", "SVX"): Decimal("0.95"),
            ("MOW", "IST"): Decimal("1.05"),
            ("MOW", "AYT"): Decimal("1.08"),
            ("MOW", "DXB"): Decimal("1.18"),
            ("MOW", "BCN"): Decimal("1.22"),
            ("MOW", "MAD"): Decimal("1.20"),
            ("MOW", "BKK"): Decimal("1.35"),
            ("MOW", "DPS"): Decimal("1.15"),
            ("MOW", "HKT"): Decimal("1.18"),
            ("MOW", "SGN"): Decimal("1.20"),
            ("MOW", "CXR"): Decimal("1.15"),
            ("MOW", "MLE"): Decimal("1.22"),
            ("MOW", "HRG"): Decimal("1.12"),
            ("LED", "AER"): Decimal("1.05"),
            ("LED", "IST"): Decimal("1.12"),
            ("SVX", "AER"): Decimal("1.08"),
            ("SVX", "DXB"): Decimal("1.25"),
        }
        if route in modifiers:
            return modifiers[route]
        hubs = {"MOW", "LED"}
        if origin_iata not in hubs:
            return Decimal("1.12")
        return Decimal("1.00")

    @staticmethod
    def _money(value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"))


class TravelpayoutsPricingProvider:
    def __init__(self, fallback: MockPricingProvider | None = None) -> None:
        self.settings = get_settings()
        self.fallback = fallback or MockPricingProvider()
        self._hotel_resolver = HotelPriceResolver()

    def get_quote(
        self,
        destination: str,
        people_count: int,
        travel_type: TravelType,
        comfort_level: ComfortLevel | None,
        start_date: date | None = None,
        end_date: date | None = None,
        origin: str | None = None,
    ) -> PriceQuote:
        quote = self.fallback.get_quote(
            destination=destination,
            people_count=people_count,
            travel_type=travel_type,
            comfort_level=comfort_level,
            start_date=start_date,
            end_date=end_date,
            origin=origin,
        )
        token = self.settings.travelpayouts_token
        if not token:
            return quote

        flight_price: Decimal | None = None
        flight_source = quote.flight_source
        flight_airline: str | None = None
        flight_ticket_url: str | None = None
        flight_link_is_specific = False
        destination_iata = resolve_iata(destination)
        origin_iata = resolve_origin_iata(origin)
        if destination_iata and start_date is not None:
            flight_price, flight_source, flight_airline, flight_ticket_url = self._fetch_flight_price(
                origin=origin_iata,
                destination=destination_iata,
                depart_date=start_date,
                return_date=end_date,
                token=token,
            )
            flight_link_is_specific = flight_ticket_url is not None

        if flight_price is None and destination_iata:
            flight_price = self.fallback.estimate_flight_per_person(
                origin,
                destination,
                travel_type=travel_type,
            )
            flight_source = "ориентировочно (оценка по маршруту)"

        hotel_per_night, accommodation_source, hotel_name, hotel_booking_url = self._resolve_hotel_rate(
            destination=destination,
            comfort_level=comfort_level,
            start_date=start_date,
            end_date=end_date,
            people_count=people_count,
            fallback_nightly=quote.hotel_per_night,
            fallback_source=quote.accommodation_source,
        )
        hotel_link_is_specific = bool(
            hotel_booking_url
            and hotel_name
            and "search.hotellook.com/hotels" not in hotel_booking_url
        )

        flight_booking_url = flight_ticket_url or (
            build_flight_link(
                destination,
                start_date,
                end_date,
                people_count,
                origin_iata=origin_iata,
                airline=flight_airline,
            )
            if destination_iata and start_date and end_date
            else None
        )

        parts = []
        if flight_price is not None:
            parts.append("flights")
        if accommodation_source.startswith("Google Hotels"):
            parts.append("serpapi-hotels")
        elif accommodation_source.startswith("Makcorps"):
            parts.append("makcorps-hotels")
        elif accommodation_source.startswith("Hotellook"):
            parts.append("hotellook")
        elif "catalog" in accommodation_source:
            parts.append("catalog-hotels")
        else:
            parts.append("mock-stay")
        combined_source = "travelpayouts+" + "+".join(parts) if parts else quote.source

        return PriceQuote(
            flight_per_person=flight_price if flight_price is not None else quote.flight_per_person,
            hotel_per_night=hotel_per_night,
            daily_food_per_person=quote.daily_food_per_person,
            daily_transport_per_person=quote.daily_transport_per_person,
            base_activities=quote.base_activities,
            source=combined_source,
            flight_source=flight_source,
            accommodation_source=accommodation_source,
            food_source=quote.food_source,
            transport_source=quote.transport_source,
            flight_airline=flight_airline,
            flight_booking_url=flight_booking_url,
            flight_link_is_specific=flight_link_is_specific,
            hotel_name=hotel_name,
            hotel_booking_url=hotel_booking_url,
            hotel_link_is_specific=hotel_link_is_specific,
        )

    def _resolve_hotel_rate(
        self,
        destination: str,
        comfort_level: ComfortLevel | None,
        start_date: date | None,
        end_date: date | None,
        people_count: int,
        fallback_nightly: Decimal,
        fallback_source: str,
    ) -> tuple[Decimal, str, str | None, str | None]:
        if start_date and end_date and end_date > start_date:
            live = self._hotel_resolver.fetch(
                destination, start_date, end_date, adults=max(people_count, 1)
            )
            if live is not None:
                if HotelPriceResolver.is_live_source(live.source):
                    return live.price_per_night, live.source, live.hotel_name, live.booking_url
                adjusted = (live.price_per_night * comfort_multiplier(comfort_level)).quantize(
                    Decimal("0.01")
                )
                return adjusted, live.source, live.hotel_name, live.booking_url

        catalog = MockPricingProvider._catalog_hotel_rate(destination, comfort_level)
        if catalog is not None:
            return catalog, "Voyago catalog (средние цены по направлению)", None, None

        return fallback_nightly, fallback_source, None, None

    def _fetch_flight_price(
        self,
        origin: str,
        destination: str,
        depart_date: date,
        return_date: date | None,
        token: str,
    ) -> tuple[Decimal | None, str, str | None, str | None]:
        settings = get_settings()
        for depart_key, return_key in self._flight_date_attempts(depart_date, return_date):
            exact, airline, ticket_link = self._fetch_cheap_price(
                origin,
                destination,
                depart_key,
                return_key,
                token,
            )
            if exact is not None:
                ticket_url = resolve_aviasales_ticket_link(ticket_link, settings.travelpayouts_marker)
                return exact, "Travelpayouts / Aviasales cache", airline, ticket_url

        if return_date is not None and return_date > depart_date:
            matrix = self._fetch_matrix_roundtrip(origin, destination, depart_date, return_date, token)
            if matrix is not None:
                return matrix, "Travelpayouts / Aviasales (кэш, ближайшие даты)", None, None

        return None, "mock", None, None

    @staticmethod
    def _flight_date_attempts(
        depart_date: date,
        return_date: date | None,
    ) -> list[tuple[str, str | None]]:
        attempts: list[tuple[str, str | None]] = [
            (depart_date.isoformat(), return_date.isoformat() if return_date else None),
        ]
        if return_date is not None:
            attempts.append(
                (depart_date.strftime("%Y-%m"), return_date.strftime("%Y-%m")),
            )
        return attempts

    def _fetch_cheap_price(
        self,
        origin: str,
        destination: str,
        depart_date: str,
        return_date: str | None,
        token: str,
    ) -> tuple[Decimal | None, str | None, str | None]:
        params: dict[str, str] = {
            "origin": origin,
            "destination": destination,
            "depart_date": depart_date,
            "currency": "RUB",
            "token": token,
        }
        if return_date is not None:
            params["return_date"] = return_date
        headers = {"X-Access-Token": token}
        try:
            response = httpx.get(
                "https://api.travelpayouts.com/v1/prices/cheap",
                params=params,
                headers=headers,
                timeout=8.0,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError):
            return None, None, None

        data = payload.get("data", {})
        destination_data = data.get(destination, {}) if isinstance(data, dict) else {}
        best_price: Decimal | None = None
        best_airline: str | None = None
        best_link: str | None = None
        if isinstance(destination_data, dict):
            for item in destination_data.values():
                if not isinstance(item, dict) or not item.get("price"):
                    continue
                price = Decimal(str(item["price"])).quantize(Decimal("0.01"))
                if best_price is None or price < best_price:
                    best_price = price
                    best_airline = item.get("airline")
                    raw_link = item.get("link")
                    best_link = str(raw_link) if raw_link else None
        if best_price is None:
            return None, None, None
        return best_price, str(best_airline) if best_airline else None, best_link

    def _fetch_matrix_roundtrip(
        self,
        origin: str,
        destination: str,
        depart_date: date,
        return_date: date,
        token: str,
        window_days: int = 3,
    ) -> Decimal | None:
        outbound = self._matrix_leg_min(origin, destination, depart_date, token, window_days)
        inbound = self._matrix_leg_min(destination, origin, return_date, token, window_days)
        if outbound is None or inbound is None:
            return None
        return (outbound + inbound).quantize(Decimal("0.01"))

    @staticmethod
    def _matrix_leg_min(
        origin: str,
        destination: str,
        target: date,
        token: str,
        window_days: int,
    ) -> Decimal | None:
        try:
            response = httpx.get(
                "https://api.travelpayouts.com/v2/prices/month-matrix",
                params={
                    "origin": origin,
                    "destination": destination,
                    "currency": "rub",
                    "token": token,
                    "limit": 100,
                },
                timeout=5,
            )
            response.raise_for_status()
            rows = response.json().get("data", [])
        except (httpx.HTTPError, ValueError):
            return None

        best: Decimal | None = None
        for row in rows:
            if not isinstance(row, dict) or not row.get("value") or not row.get("depart_date"):
                continue
            try:
                leg_date = date.fromisoformat(str(row["depart_date"]))
                value = Decimal(str(row["value"]))
            except (ValueError, TypeError):
                continue
            if abs((leg_date - target).days) > window_days:
                continue
            if best is None or value < best:
                best = value
        return best


def create_pricing_provider() -> PricingProvider:
    settings = get_settings()
    if settings.pricing_provider.lower() in {"travelpayouts", "aviasales", "real"}:
        return TravelpayoutsPricingProvider()
    return MockPricingProvider()


def integration_status() -> list[dict[str, str | bool]]:
    settings = get_settings()
    has_token = bool(settings.travelpayouts_token)
    has_catalog = bool(HOTEL_CATALOG_RATES)
    has_serpapi = bool(settings.serpapi_api_key)
    has_makcorps = bool(
        settings.makcorps_jwt
        or (settings.makcorps_username and settings.makcorps_password)
    )
    hotel_live = has_serpapi or has_makcorps or has_token
    return [
        {
            "code": "travelpayouts",
            "title": "Aviasales / Travelpayouts",
            "type": "flights",
            "enabled": has_token,
            "status": "реальные цены на перелёт" if has_token else "нужен TRAVELPAYOUTS_TOKEN",
        },
        {
            "code": "serpapi-hotels",
            "title": "Google Hotels (SerpApi)",
            "type": "hotels",
            "enabled": has_serpapi,
            "status": (
                "минимальная цена по датам поездки (RUB)"
                if has_serpapi
                else "нужен SERPAPI_API_KEY — https://serpapi.com"
            ),
        },
        {
            "code": "makcorps-hotels",
            "title": "Makcorps Free Hotel API",
            "type": "hotels",
            "enabled": has_makcorps,
            "status": (
                "цены Booking/Priceline (без дат в free tier)"
                if has_makcorps
                else "нужны MAKCORPS_USERNAME и MAKCORPS_PASSWORD"
            ),
        },
        {
            "code": "hotellook",
            "title": "Hotellook / Travelpayouts",
            "type": "hotels",
            "enabled": has_token,
            "status": "резерв, если SerpApi/Makcorps недоступны",
        },
        {
            "code": "hotel-catalog",
            "title": "Каталог средних цен Voyago",
            "type": "hotels",
            "enabled": has_catalog,
            "status": f"fallback, направлений: {len(HOTEL_CATALOG_RATES)}",
        },
        {
            "code": "daily-costs-catalog",
            "title": "Каталог питания и транспорта (Numbeo + Росстат, 2026)",
            "type": "daily_costs",
            "enabled": True,
            "status": "дневные траты по направлению и уровню комфорта",
        },
        {
            "code": "ranvik-ai",
            "title": "Ranvik AI (DeepSeek)",
            "type": "ai",
            "enabled": bool(settings.ranvik_api_key),
            "status": (
                f"работает — {settings.ranvik_model}"
                if settings.ranvik_api_key
                else "нужен RANVIK_API_KEY — api.ranvik.ru"
            ),
        },
        {
            "code": "groq-ai",
            "title": "Groq AI (чат и советы)",
            "type": "ai",
            "enabled": bool(settings.groq_api_key),
            "status": (
                "работает — Llama 3.3"
                if settings.groq_api_key
                else "нужен GROQ_API_KEY — console.groq.com (бесплатно, работает в РФ)"
            ),
        },
        {
            "code": "gemini-ai",
            "title": "Google Gemini",
            "type": "ai",
            "enabled": bool(settings.gemini_api_key),
            "status": (
                "ключ задан (может быть недоступен в РФ — используйте Groq)"
                if settings.gemini_api_key
                else "нужен GEMINI_API_KEY"
            ),
        },
        {
            "code": "booking",
            "title": "Booking.com",
            "type": "hotels",
            "enabled": False,
            "status": "партнёрский Demand API (отдельный договор)",
        },
        {
            "code": "airbnb",
            "title": "Airbnb",
            "type": "apartments",
            "enabled": False,
            "status": "только партнёрская программа",
        },
    ]

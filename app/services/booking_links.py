"""Partner deep links tied to a concrete search variant."""

from __future__ import annotations

from datetime import date
from urllib.parse import quote, urlencode

from app.core.config import get_settings
from app.services.iata_codes import resolve_iata
from app.services.serpapi_hotels_client import CITY_QUERY

AVIASALES_SEARCH = "https://www.aviasales.ru/search"
HOTELLOOK_SEARCH = "https://search.hotellook.com/hotels"
GOOGLE_HOTELS_SEARCH = "https://www.google.com/travel/search"


def _segment(iata: str, when: date) -> str:
    return f"{iata.upper()}{when.day:02d}{when.month:02d}"


def build_flight_link(
    destination: str,
    start_date: date,
    end_date: date,
    people_count: int,
    *,
    origin_iata: str | None = None,
    airline: str | None = None,
    override_url: str | None = None,
) -> str | None:
    if override_url:
        return override_url
    settings = get_settings()
    origin = (origin_iata or settings.default_origin_iata).upper()
    dest_iata = resolve_iata(destination)
    if not dest_iata:
        return None
    adults = max(people_count, 1)
    marker = settings.travelpayouts_marker
    path = f"{_segment(origin, start_date)}{_segment(dest_iata, end_date)}{adults}"
    query: dict[str, str] = {
        "origin_iata": origin,
        "destination_iata": dest_iata,
        "depart_date": start_date.isoformat(),
        "return_date": end_date.isoformat(),
        "adults": str(adults),
        "currency": "RUB",
    }
    if marker:
        query["marker"] = marker
    if airline:
        query["airline"] = airline
    return f"{AVIASALES_SEARCH}/{path}?{urlencode(query)}"


def build_hotel_links(
    destination: str,
    start_date: date,
    end_date: date,
    people_count: int,
    *,
    hotel_name: str | None = None,
    property_url: str | None = None,
) -> dict[str, str | None]:
    settings = get_settings()
    marker = settings.travelpayouts_marker
    adults = max(people_count, 1)
    city = CITY_QUERY.get(destination.strip().lower()) or destination.strip()

    if property_url:
        primary_hotel = property_url
    elif hotel_name:
        q = quote(f"{hotel_name} {city}")
        primary_hotel = (
            f"https://www.google.com/travel/hotels/{quote(city)}"
            f"?hl=ru&gl=ru&dates={start_date.isoformat()},{end_date.isoformat()}"
            f"&q={q}&travelers={adults}"
        )
    else:
        hotel_params = {
            "destination": city,
            "checkIn": start_date.isoformat(),
            "checkOut": end_date.isoformat(),
            "adults": str(adults),
            "children": "0",
            "currency": "rub",
            "language": "ru",
        }
        if marker:
            hotel_params["marker"] = marker
        primary_hotel = HOTELLOOK_SEARCH + "?" + urlencode(hotel_params)

    google_params = {
        "q": quote(hotel_name or f"отели {city}"),
        "dates": f"{start_date.isoformat()},{end_date.isoformat()}",
        "travelers": str(adults),
        "hl": "ru",
        "gl": "ru",
        "currency": "RUB",
    }
    hl_params = {
        "destination": city,
        "checkIn": start_date.isoformat(),
        "checkOut": end_date.isoformat(),
        "adults": str(adults),
        "currency": "rub",
        "language": "ru",
    }
    if marker:
        hl_params["marker"] = marker
    return {
        "flight_aviasales": None,
        "hotel_primary": primary_hotel,
        "hotel_hotellook": HOTELLOOK_SEARCH + "?" + urlencode(hl_params),
        "hotel_google": GOOGLE_HOTELS_SEARCH + "?" + urlencode(google_params),
        "hotel_name": hotel_name,
    }


def build_booking_links(
    destination: str,
    start_date: date,
    end_date: date,
    people_count: int,
    *,
    origin_iata: str | None = None,
    flight_airline: str | None = None,
    flight_booking_url: str | None = None,
    hotel_name: str | None = None,
    hotel_booking_url: str | None = None,
) -> dict[str, str | None]:
    hotels = build_hotel_links(
        destination,
        start_date,
        end_date,
        people_count,
        hotel_name=hotel_name,
        property_url=hotel_booking_url,
    )
    hotels["flight_aviasales"] = build_flight_link(
        destination,
        start_date,
        end_date,
        people_count,
        origin_iata=origin_iata,
        airline=flight_airline,
        override_url=flight_booking_url,
    )
    return hotels

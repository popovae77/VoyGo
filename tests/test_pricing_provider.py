from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.models.enums import ComfortLevel, TravelType
from app.services.hotel_price_types import HotelPriceResult
from app.services.pricing_provider import (
    HOTEL_CATALOG_RATES,
    MockPricingProvider,
    TravelpayoutsPricingProvider,
)


def test_catalog_hotel_rate_for_sochi():
    provider = MockPricingProvider()
    quote = provider.get_quote(
        destination="Сочи",
        people_count=2,
        travel_type=TravelType.beach,
        comfort_level=ComfortLevel.standard,
    )
    assert quote.hotel_per_night == HOTEL_CATALOG_RATES["сочи"]
    assert "catalog" in quote.accommodation_source


def test_travelpayouts_uses_hotellook_when_available():
    start = date.today() + timedelta(days=30)
    end = start + timedelta(days=5)
    fallback = MockPricingProvider()
    provider = TravelpayoutsPricingProvider(fallback=fallback)
    provider.settings = MagicMock(travelpayouts_token="test-token", default_origin_iata="MOW")
    provider._hotel_resolver = MagicMock()
    provider._hotel_resolver.fetch.return_value = HotelPriceResult(
        price_per_night=Decimal("4800.00"),
        source="Hotellook / Travelpayouts",
    )
    provider._fetch_flight_price = MagicMock(return_value=(None, "mock", None))

    quote = provider.get_quote(
        destination="Сочи",
        people_count=2,
        travel_type=TravelType.beach,
        comfort_level=ComfortLevel.standard,
        start_date=start,
        end_date=end,
    )
    assert quote.hotel_per_night == Decimal("4800.00")
    assert quote.accommodation_source == "Hotellook / Travelpayouts"


def test_travelpayouts_falls_back_to_catalog_when_hotellook_empty():
    start = date.today() + timedelta(days=30)
    end = start + timedelta(days=5)
    provider = TravelpayoutsPricingProvider()
    provider.settings = MagicMock(travelpayouts_token="test-token", default_origin_iata="MOW")
    provider._hotel_resolver = MagicMock()
    provider._hotel_resolver.fetch.return_value = None
    provider._fetch_flight_price = MagicMock(return_value=(None, "mock", None))

    quote = provider.get_quote(
        destination="Сочи",
        people_count=2,
        travel_type=TravelType.beach,
        comfort_level=ComfortLevel.standard,
        start_date=start,
        end_date=end,
    )
    assert quote.hotel_per_night == HOTEL_CATALOG_RATES["сочи"]
    assert "catalog" in quote.accommodation_source


def test_bali_flight_estimate_is_realistic_for_long_haul():
    price = MockPricingProvider.estimate_flight_per_person("Москва", "Бали")
    assert price >= Decimal("65000")


def test_travelpayouts_uses_route_estimate_when_api_misses():
    start = date.today() + timedelta(days=30)
    end = start + timedelta(days=14)
    provider = TravelpayoutsPricingProvider()
    provider.settings = MagicMock(travelpayouts_token="test-token", default_origin_iata="MOW")
    provider._hotel_resolver = MagicMock()
    provider._hotel_resolver.fetch.return_value = None
    provider._fetch_flight_price = MagicMock(return_value=(None, "mock", None))

    quote = provider.get_quote(
        destination="Бали",
        people_count=2,
        travel_type=TravelType.beach,
        comfort_level=ComfortLevel.standard,
        start_date=start,
        end_date=end,
        origin="Москва",
    )
    assert quote.flight_per_person >= Decimal("65000")
    assert "оценка по маршруту" in quote.flight_source

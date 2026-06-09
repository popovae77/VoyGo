from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.models.enums import ComfortLevel, TravelType
from app.services.ai_advisor import _ai_provider, chat_with_ai
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
    assert quote.daily_food_per_person == Decimal("3600.00")
    assert quote.daily_transport_per_person == Decimal("850.00")
    assert "Numbeo" in quote.food_source


def test_sochi_food_and_transport_scale_with_trip_length():
    from app.core.database import SessionLocal
    from app.services.budget_calculator import BudgetCalculatorService
    from app.schemas.trip import TripSearchCreate

    start = date.today() + timedelta(days=30)
    end = start + timedelta(days=7)
    trip = TripSearchCreate(
        destination="Сочи",
        origin="Москва",
        start_date=start,
        end_date=end,
        people_count=2,
        budget=Decimal("500000"),
        travel_type=TravelType.beach,
        comfort_level=ComfortLevel.standard,
    )
    db = SessionLocal()
    try:
        offer = BudgetCalculatorService(db, pricing_provider=MockPricingProvider()).calculate(trip)
    finally:
        db.close()

    assert offer.breakdown.food == Decimal("50400.00")
    assert offer.breakdown.local_transport == Decimal("10115.00")


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
    provider._fetch_flight_price = MagicMock(return_value=(None, "mock", None, None))

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
    provider._fetch_flight_price = MagicMock(return_value=(None, "mock", None, None))

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
    provider._fetch_flight_price = MagicMock(return_value=(None, "mock", None, None))

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


def test_ranvik_is_preferred_ai_provider():
    settings = MagicMock(
        ranvik_api_key="rk_live_test",
        groq_api_key="gsk_test",
        gemini_api_key="gemini_test",
    )
    assert _ai_provider(settings) == "ranvik"


@patch("app.services.ai_advisor._ranvik_chat", return_value="Привет! Поездка в Сочи выгодна.")
@patch("app.services.ai_advisor.get_settings")
def test_chat_with_ranvik(mock_settings, mock_ranvik):
    mock_settings.return_value = MagicMock(
        ranvik_api_key="rk_live_test",
        groq_api_key=None,
        gemini_api_key=None,
        ranvik_model="deepseek-v4-flash",
        ranvik_api_url="https://api.ranvik.ru/v1/chat/completions",
    )
    reply = chat_with_ai("Куда поехать?", [], trip_context=None)
    assert "Сочи" in reply
    mock_ranvik.assert_called_once()

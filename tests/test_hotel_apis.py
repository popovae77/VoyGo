from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

from app.models.enums import ComfortLevel, TravelType
from app.services.hotel_price_types import HotelPriceResult
from app.services.makcorps_client import MakcorpsClient
from app.services.pricing_provider import TravelpayoutsPricingProvider
from app.services.serpapi_hotels_client import SerpApiHotelsClient


SAMPLE_MAKCORPS = [
    {"hotelName": "Test Hotel", "hotelId": "1"},
    [
        {"price1": "100", "tax1": "10", "vendor1": "Booking.com"},
        {"price2": "80", "tax2": "0", "vendor2": "Priceline"},
    ],
]

SAMPLE_SERPAPI = {
    "properties": [
        {
            "name": "Hotel A",
            "rate_per_night": {"lowest": "5000 ₽", "extracted_lowest": 5000},
        },
        {
            "name": "Hotel B",
            "rate_per_night": {"extracted_lowest": 4200},
        },
    ]
}


def test_makcorps_min_price_parser():
    assert MakcorpsClient._min_vendor_price(SAMPLE_MAKCORPS) == Decimal("80")


def test_serpapi_min_price_parser():
    picked = SerpApiHotelsClient._pick_best_property(SAMPLE_SERPAPI)
    assert picked is not None
    assert picked[0] == Decimal("4200.00")
    assert picked[1] == "Hotel B"


def test_travelpayouts_uses_serpapi_live_price_without_comfort_discount():
    start = date.today() + timedelta(days=30)
    end = start + timedelta(days=5)
    provider = TravelpayoutsPricingProvider()
    provider.settings = MagicMock(travelpayouts_token="test-token", default_origin_iata="MOW")
    provider._hotel_resolver = MagicMock()
    provider._hotel_resolver.fetch.return_value = HotelPriceResult(
        price_per_night=Decimal("4200.00"),
        source="Google Hotels / SerpApi",
    )
    provider._fetch_flight_price = MagicMock(return_value=(None, "mock", None, None))

    quote = provider.get_quote(
        destination="Сочи",
        people_count=2,
        travel_type=TravelType.beach,
        comfort_level=ComfortLevel.economy,
        start_date=start,
        end_date=end,
    )
    assert quote.hotel_per_night == Decimal("4200.00")
    assert quote.accommodation_source == "Google Hotels / SerpApi"

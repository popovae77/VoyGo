from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class HotelPriceResult:
    price_per_night: Decimal
    source: str
    location_id: int | None = None
    hotel_name: str | None = None
    booking_url: str | None = None

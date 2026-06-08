from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.enums import ComfortLevel, TravelType
from app.models.trip import TravelTypeCoefficient
from app.schemas.trip import BudgetBreakdown, TripSearchCreate
from app.services.booking_links import build_booking_links
from app.services.iata_codes import resolve_origin_iata
from app.services.pricing_provider import PricingProvider, create_pricing_provider


TRAVEL_TYPE_TITLES: dict[TravelType, str] = {
    TravelType.beach: "Пляжный",
    TravelType.active: "Активный",
    TravelType.excursion: "Экскурсионный",
    TravelType.city: "Городской",
    TravelType.family: "Семейный",
    TravelType.cruise: "Круиз",
    TravelType.other: "Другой",
}

DEFAULT_COEFFICIENTS: dict[TravelType, tuple[Decimal, Decimal, Decimal]] = {
    TravelType.beach: (Decimal("0.85"), Decimal("0.90"), Decimal("1.00")),
    TravelType.active: (Decimal("1.25"), Decimal("1.45"), Decimal("1.10")),
    TravelType.excursion: (Decimal("1.10"), Decimal("1.35"), Decimal("1.00")),
    TravelType.city: (Decimal("1.20"), Decimal("1.10"), Decimal("1.05")),
    TravelType.family: (Decimal("1.00"), Decimal("0.95"), Decimal("1.20")),
    TravelType.cruise: (Decimal("0.70"), Decimal("1.50"), Decimal("1.15")),
    TravelType.other: (Decimal("1.00"), Decimal("1.00"), Decimal("1.00")),
}


@dataclass
class CalculatedOffer:
    title: str
    total_price: Decimal
    fits_budget: bool
    breakdown: BudgetBreakdown
    note: str | None = None
    source: str = "mock"
    flight_source: str = "mock"
    accommodation_source: str = "mock"
    calculation_details: dict | None = None
    booking_links: dict | None = None


class BudgetCalculatorService:
    def __init__(self, db: Session, pricing_provider: PricingProvider | None = None) -> None:
        self.db = db
        self.pricing_provider = pricing_provider or create_pricing_provider()
        self.settings = get_settings()

    def calculate(self, trip: TripSearchCreate, note: str | None = None) -> CalculatedOffer:
        days = max((trip.end_date - trip.start_date).days, 1)
        quote = self.pricing_provider.get_quote(
            destination=trip.destination,
            people_count=trip.people_count,
            travel_type=trip.travel_type,
            comfort_level=trip.comfort_level,
            start_date=trip.start_date,
            end_date=trip.end_date,
            origin=trip.origin,
        )
        coeff = self._get_coefficients(trip.travel_type)

        flight = quote.flight_per_person * trip.people_count
        hotel = quote.hotel_per_night * days
        food = quote.daily_food_per_person * days * trip.people_count * coeff.food_coeff
        local_transport = quote.base_local_transport * coeff.transport_coeff
        activities = quote.base_activities * coeff.activities_coeff * trip.people_count
        insurance = (flight + hotel) * Decimal("0.03")
        subtotal = flight + hotel + food + local_transport + activities + insurance
        reserve = subtotal * (Decimal(self.settings.reserve_percent) / Decimal("100"))
        total = self._money(subtotal + reserve)

        breakdown = BudgetBreakdown(
            flight=self._money(flight),
            hotel=self._money(hotel),
            food=self._money(food),
            local_transport=self._money(local_transport),
            activities=self._money(activities),
            insurance=self._money(insurance),
            reserve=self._money(reserve),
            total=total,
            days=days,
            nights=days,
        )
        comfort_label = {
            ComfortLevel.economy: "Эконом",
            ComfortLevel.standard: "Стандарт",
            ComfortLevel.comfort: "Комфорт",
            None: "Стандарт",
        }[trip.comfort_level]
        title = f"{trip.destination.strip().capitalize()} · {TRAVEL_TYPE_TITLES[trip.travel_type].lower()} отдых · {comfort_label.lower()}"
        return CalculatedOffer(
            title=title,
            total_price=total,
            fits_budget=total <= trip.budget,
            breakdown=breakdown,
            note=note,
            source=quote.source,
            flight_source=quote.flight_source,
            accommodation_source=quote.accommodation_source,
            calculation_details=build_calculation_details(
                trip=trip,
                quote=quote,
                coeff=coeff,
                days=days,
                amounts={
                    "flight": self._money(flight),
                    "hotel": self._money(hotel),
                    "food": self._money(food),
                    "local_transport": self._money(local_transport),
                    "activities": self._money(activities),
                    "insurance": self._money(insurance),
                    "reserve": self._money(reserve),
                },
                reserve_percent=self.settings.reserve_percent,
            ),
            booking_links=build_booking_links(
                trip.destination,
                trip.start_date,
                trip.end_date,
                trip.people_count,
                origin_iata=resolve_origin_iata(trip.origin),
                flight_airline=quote.flight_airline,
                flight_booking_url=quote.flight_booking_url,
                hotel_name=quote.hotel_name,
                hotel_booking_url=quote.hotel_booking_url,
            ),
        )

    def calculate_with_alternatives(self, trip: TripSearchCreate) -> list[CalculatedOffer]:
        offers = [self.calculate(trip, note="Основной вариант")]
        if offers[0].fits_budget:
            return offers

        candidates: list[TripSearchCreate] = []
        if trip.comfort_level in {ComfortLevel.standard, ComfortLevel.comfort}:
            candidates.append(trip.model_copy(update={"comfort_level": ComfortLevel.economy}))
        if (trip.end_date - trip.start_date).days > 3:
            candidates.append(trip.model_copy(update={"end_date": trip.end_date - timedelta(days=2)}))
        candidates.append(
            trip.model_copy(
                update={
                    "start_date": trip.start_date + timedelta(days=7),
                    "end_date": trip.end_date + timedelta(days=7),
                }
            )
        )

        notes = [
            "Альтернатива: уровень комфорта эконом",
            "Альтернатива: поездка на 2 дня короче",
            "Альтернатива: сдвиг дат на неделю",
        ]
        alternatives = [self.calculate(candidate, note=notes[index]) for index, candidate in enumerate(candidates)]
        alternatives.sort(key=lambda item: item.total_price)
        return offers + alternatives[:3]

    def _get_coefficients(self, travel_type: TravelType) -> TravelTypeCoefficient:
        coefficient = self.db.scalar(
            select(TravelTypeCoefficient).where(TravelTypeCoefficient.travel_type == travel_type.value)
        )
        if coefficient is not None:
            return coefficient
        transport, activities, food = DEFAULT_COEFFICIENTS[travel_type]
        return TravelTypeCoefficient(
            travel_type=travel_type.value,
            transport_coeff=transport,
            activities_coeff=activities,
            food_coeff=food,
        )

    @staticmethod
    def _money(value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"))


def _fmt(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):,.0f}".replace(",", " ")


def build_calculation_details(
    trip: TripSearchCreate,
    quote,
    coeff: TravelTypeCoefficient,
    days: int,
    amounts: dict[str, Decimal],
    reserve_percent: int,
) -> dict:
    travel_title = TRAVEL_TYPE_TITLES[trip.travel_type]
    subtotal = (
        amounts["flight"]
        + amounts["hotel"]
        + amounts["food"]
        + amounts["local_transport"]
        + amounts["activities"]
        + amounts["insurance"]
    )
    return {
        "flight": {
            "title": "Перелёт",
            "total": str(amounts["flight"]),
            "lines": [
                f"Маршрут: {trip.origin.strip()} → {trip.destination.strip()}",
                f"Источник: {quote.flight_source}",
                f"Цена на 1 человека: {_fmt(quote.flight_per_person)} ₽",
                f"Путешественников: {trip.people_count}",
                f"Расчёт: {_fmt(quote.flight_per_person)} × {trip.people_count} = {_fmt(amounts['flight'])} ₽",
            ],
        },
        "hotel": {
            "title": "Проживание",
            "total": str(amounts["hotel"]),
            "lines": [
                f"Источник: {quote.accommodation_source}",
                f"Цена за ночь: {_fmt(quote.hotel_per_night)} ₽",
                f"Ночей: {days}",
                f"Расчёт: {_fmt(quote.hotel_per_night)} × {days} = {_fmt(amounts['hotel'])} ₽",
            ],
        },
        "food": {
            "title": "Питание",
            "total": str(amounts["food"]),
            "lines": [
                f"База: {_fmt(quote.daily_food_per_person)} ₽ / чел. / день (регион и комфорт)",
                f"Коэффициент типа отдыха «{travel_title}»: ×{coeff.food_coeff}",
                f"Дней: {days}, людей: {trip.people_count}",
                (
                    f"Расчёт: {_fmt(quote.daily_food_per_person)} × {days} × {trip.people_count} "
                    f"× {coeff.food_coeff} = {_fmt(amounts['food'])} ₽"
                ),
            ],
        },
        "local_transport": {
            "title": "Транспорт на месте",
            "total": str(amounts["local_transport"]),
            "lines": [
                f"База по направлению: {_fmt(quote.base_local_transport)} ₽",
                f"Коэффициент «{travel_title}»: ×{coeff.transport_coeff}",
                f"Расчёт: {_fmt(quote.base_local_transport)} × {coeff.transport_coeff} = {_fmt(amounts['local_transport'])} ₽",
                "Включает такси, метро, трансферы внутри города (ориентир).",
            ],
        },
        "activities": {
            "title": "Активности и развлечения",
            "total": str(amounts["activities"]),
            "lines": [
                f"База: {_fmt(quote.base_activities)} ₽",
                f"Коэффициент «{travel_title}»: ×{coeff.activities_coeff}",
                f"Путешественников: {trip.people_count}",
                (
                    f"Расчёт: {_fmt(quote.base_activities)} × {coeff.activities_coeff} "
                    f"× {trip.people_count} = {_fmt(amounts['activities'])} ₽"
                ),
            ],
        },
        "insurance": {
            "title": "Страховка",
            "total": str(amounts["insurance"]),
            "lines": [
                "3% от суммы перелёта и проживания",
                f"Расчёт: ({_fmt(amounts['flight'])} + {_fmt(amounts['hotel'])}) × 0,03 = {_fmt(amounts['insurance'])} ₽",
            ],
        },
        "reserve": {
            "title": "Резерв на непредвиденное",
            "total": str(amounts["reserve"]),
            "lines": [
                f"Процент резерва: {reserve_percent}%",
                f"База (без резерва): {_fmt(subtotal)} ₽",
                f"Расчёт: {_fmt(subtotal)} × {reserve_percent}% = {_fmt(amounts['reserve'])} ₽",
            ],
        },
    }


def seed_travel_type_coefficients(db: Session) -> None:
    for travel_type, (transport, activities, food) in DEFAULT_COEFFICIENTS.items():
        existing = db.scalar(
            select(TravelTypeCoefficient).where(TravelTypeCoefficient.travel_type == travel_type.value)
        )
        if existing is None:
            db.add(
                TravelTypeCoefficient(
                    travel_type=travel_type.value,
                    transport_coeff=transport,
                    activities_coeff=activities,
                    food_coeff=food,
                )
            )
    db.commit()

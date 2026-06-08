from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import ComfortLevel, TravelType


class TripSearchCreate(BaseModel):
    origin: str = Field(default="Москва", min_length=2, max_length=255)
    destination: str = Field(min_length=2, max_length=255)
    start_date: date
    end_date: date
    people_count: int = Field(ge=1, le=10)
    budget: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    travel_type: TravelType
    comfort_level: ComfortLevel | None = ComfortLevel.standard

    @field_validator("budget")
    @classmethod
    def round_budget(cls, value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"))

    @model_validator(mode="after")
    def validate_dates(self) -> "TripSearchCreate":
        if self.end_date <= self.start_date:
            raise ValueError("Дата окончания должна быть позже даты начала")
        return self


class BudgetBreakdown(BaseModel):
    flight: Decimal
    hotel: Decimal
    food: Decimal
    local_transport: Decimal
    activities: Decimal
    insurance: Decimal
    reserve: Decimal
    total: Decimal
    days: int
    nights: int


class TripOfferRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trip_request_id: int
    title: str
    total_price: Decimal
    fits_budget: bool
    breakdown_json: dict
    source: str
    note: str | None = None
    created_at: datetime


class TripRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    origin: str
    destination: str
    start_date: date
    end_date: date
    people_count: int
    budget: Decimal
    travel_type: TravelType
    comfort_level: ComfortLevel | None
    created_at: datetime
    offers: list[TripOfferRead] = []


class AiAdviceRead(BaseModel):
    summary: str = ""
    best_pick: str = ""
    tips: list[str] = []


class TripSearchResponse(BaseModel):
    request: TripRequestRead
    offers: list[TripOfferRead]
    ai_advice: AiAdviceRead | None = None


class TravelTypeRead(BaseModel):
    code: TravelType
    title: str

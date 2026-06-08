from fastapi import APIRouter

from app.models.enums import TravelType
from app.schemas.trip import TravelTypeRead
from app.services.budget_calculator import TRAVEL_TYPE_TITLES
from app.services.destinations_catalog import DESTINATIONS
from app.services.pricing_provider import integration_status


router = APIRouter(prefix="/refs", tags=["References"])


@router.get("/destinations")
def destinations() -> list[dict[str, str]]:
    return DESTINATIONS


@router.get("/travel-types", response_model=list[TravelTypeRead])
def travel_types() -> list[TravelTypeRead]:
    return [TravelTypeRead(code=code, title=title) for code, title in TRAVEL_TYPE_TITLES.items()]


@router.get("/integrations")
def integrations() -> list[dict[str, str | bool]]:
    return integration_status()

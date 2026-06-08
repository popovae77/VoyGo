from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.trip import TripOffer, TripRequest
from app.models.user import User
from app.schemas.trip import AiAdviceRead, TripRequestRead, TripSearchCreate, TripSearchResponse
from app.services.ai_advisor import get_ai_travel_advice
from app.services.budget_calculator import BudgetCalculatorService, TRAVEL_TYPE_TITLES


router = APIRouter(prefix="/trips", tags=["Trips & Budget"])


@router.post("/search", response_model=TripSearchResponse, status_code=status.HTTP_201_CREATED)
def search_trips(
    payload: TripSearchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TripSearchResponse:
    trip_request = TripRequest(
        user_id=current_user.id,
        origin=payload.origin.strip(),
        destination=payload.destination.strip(),
        start_date=payload.start_date,
        end_date=payload.end_date,
        people_count=payload.people_count,
        budget=payload.budget,
        travel_type=payload.travel_type.value,
        comfort_level=payload.comfort_level.value if payload.comfort_level else None,
    )
    db.add(trip_request)
    db.commit()
    db.refresh(trip_request)

    calculator = BudgetCalculatorService(db)
    calculated_offers = calculator.calculate_with_alternatives(payload)
    offers: list[TripOffer] = []
    for calculated in calculated_offers:
        breakdown = _offer_breakdown(payload, calculated)
        offer = TripOffer(
            trip_request_id=trip_request.id,
            title=calculated.title,
            total_price=calculated.total_price,
            fits_budget=calculated.fits_budget,
            breakdown_json=breakdown,
            source=calculated.source,
            note=calculated.note,
        )
        db.add(offer)
        offers.append(offer)
    db.commit()
    for offer in offers:
        db.refresh(offer)

    trip_request = _get_user_request(db, current_user.id, trip_request.id)
    offers_payload = [
        {
            "title": o.title,
            "total_price": str(o.total_price),
            "fits_budget": o.fits_budget,
            "breakdown_json": o.breakdown_json,
        }
        for o in trip_request.offers
    ]
    ai_raw = get_ai_travel_advice(payload, offers_payload)
    return TripSearchResponse(
        request=trip_request,
        offers=trip_request.offers,
        ai_advice=AiAdviceRead(**ai_raw),
    )


@router.get("/requests", response_model=list[TripRequestRead])
def list_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TripRequest]:
    return list(
        db.scalars(
            select(TripRequest)
            .options(selectinload(TripRequest.offers))
            .where(TripRequest.user_id == current_user.id)
            .order_by(TripRequest.created_at.desc())
            .limit(20)
        )
    )


@router.get("/requests/{request_id}", response_model=TripRequestRead)
def get_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TripRequest:
    return _get_user_request(db, current_user.id, request_id)


@router.post("/requests/{request_id}/recalculate", response_model=TripSearchResponse)
def recalculate_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TripSearchResponse:
    trip_request = _get_user_request(db, current_user.id, request_id)
    payload = TripSearchCreate(
        origin=getattr(trip_request, "origin", None) or "Москва",
        destination=trip_request.destination,
        start_date=trip_request.start_date,
        end_date=trip_request.end_date,
        people_count=trip_request.people_count,
        budget=trip_request.budget,
        travel_type=trip_request.travel_type,
        comfort_level=trip_request.comfort_level,
    )
    for offer in list(trip_request.offers):
        db.delete(offer)
    db.flush()

    offers: list[TripOffer] = []
    for calculated in BudgetCalculatorService(db).calculate_with_alternatives(payload):
        breakdown = _offer_breakdown(payload, calculated)
        offer = TripOffer(
            trip_request_id=trip_request.id,
            title=calculated.title,
            total_price=calculated.total_price,
            fits_budget=calculated.fits_budget,
            breakdown_json=breakdown,
            source=calculated.source,
            note=calculated.note,
        )
        db.add(offer)
        offers.append(offer)
    db.commit()
    for offer in offers:
        db.refresh(offer)

    trip_request = _get_user_request(db, current_user.id, request_id)
    return TripSearchResponse(request=trip_request, offers=trip_request.offers)


def _get_user_request(db: Session, user_id: int, request_id: int) -> TripRequest:
    trip_request = db.scalar(
        select(TripRequest)
        .options(selectinload(TripRequest.offers))
        .where(TripRequest.id == request_id, TripRequest.user_id == user_id)
    )
    if trip_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запрос не найден")
    return trip_request


def _offer_breakdown(payload: TripSearchCreate, calculated) -> dict:
    breakdown = jsonable_encoder(calculated.breakdown)
    difference = calculated.total_price - payload.budget
    breakdown["sources"] = {
        "flight": calculated.flight_source,
        "accommodation": calculated.accommodation_source,
    }
    breakdown["trip"] = {
        "origin": payload.origin.strip(),
        "destination": payload.destination.strip().capitalize(),
        "start_date": payload.start_date.isoformat(),
        "end_date": payload.end_date.isoformat(),
        "people_count": payload.people_count,
        "budget": str(payload.budget),
        "budget_difference": str(difference),
        "travel_type_title": TRAVEL_TYPE_TITLES[payload.travel_type],
        "comfort_title": {
            "economy": "Эконом",
            "standard": "Стандарт",
            "comfort": "Комфорт",
        }.get(payload.comfort_level.value if payload.comfort_level else "standard", "Стандарт"),
    }
    if calculated.calculation_details:
        breakdown["calculation_details"] = calculated.calculation_details
    if calculated.booking_links:
        breakdown["booking_links"] = calculated.booking_links
    return breakdown

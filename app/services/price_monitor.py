from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.notification import PriceAlert
from app.models.trip import TripOffer
from app.schemas.trip import TripSearchCreate
from app.services.budget_calculator import BudgetCalculatorService
from app.services.notifier import NotifierService
from app.services.pricing_provider import PricingProvider, create_pricing_provider


class PriceMonitorService:
    def __init__(self, db: Session, pricing_provider: PricingProvider | None = None) -> None:
        self.db = db
        self.pricing_provider = pricing_provider or create_pricing_provider()
        self.notifier = NotifierService(db)

    def check_price_alerts(self) -> int:
        alerts = self.db.scalars(
            select(PriceAlert)
            .options(selectinload(PriceAlert.trip_request), selectinload(PriceAlert.user))
            .where(PriceAlert.is_active.is_(True))
        ).all()
        created = 0
        for alert in alerts:
            request = alert.trip_request
            old_offer = self.db.scalar(
                select(TripOffer)
                .where(TripOffer.trip_request_id == request.id)
                .order_by(TripOffer.total_price.asc())
            )
            if old_offer is None:
                continue

            search = TripSearchCreate(
                origin=getattr(request, "origin", None) or "Москва",
                destination=request.destination,
                start_date=request.start_date,
                end_date=request.end_date,
                people_count=request.people_count,
                budget=request.budget,
                travel_type=request.travel_type,
                comfort_level=request.comfort_level,
            )
            new_offer = BudgetCalculatorService(self.db, self.pricing_provider).calculate(search)
            threshold = Decimal("1.00") - (Decimal(alert.threshold_percent) / Decimal("100"))
            if new_offer.total_price <= old_offer.total_price * threshold:
                message = (
                    f"Цена на поездку в {request.destination} снизилась до "
                    f"{new_offer.total_price} RUB. Порог уведомления: {alert.threshold_percent}%."
                )
                self.notifier.notify_price_drop(
                    alert.user,
                    trip_request_id=request.id,
                    message=message,
                    destination=request.destination,
                )
                created += 1
        return created

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.notification import Notification, PriceAlert
from app.models.trip import TripRequest
from app.models.user import User
from app.schemas.notification import NotificationRead, PriceAlertCreate, PriceAlertRead


router = APIRouter(tags=["Notifications"])


@router.get("/notifications", response_model=list[NotificationRead])
def list_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Notification]:
    return list(
        db.scalars(
            select(Notification)
            .where(Notification.user_id == current_user.id)
            .order_by(Notification.sent_at.desc())
        )
    )


@router.patch("/notifications/{notification_id}/read", response_model=NotificationRead)
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Notification:
    notification = db.scalar(
        select(Notification).where(Notification.id == notification_id, Notification.user_id == current_user.id)
    )
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Уведомление не найдено")
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


@router.post("/alerts", response_model=PriceAlertRead, status_code=status.HTTP_201_CREATED)
def create_alert(
    payload: PriceAlertCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PriceAlert:
    trip_request = db.scalar(
        select(TripRequest).where(
            TripRequest.id == payload.trip_request_id,
            TripRequest.user_id == current_user.id,
        )
    )
    if trip_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запрос поездки не найден")
    alert = PriceAlert(
        user_id=current_user.id,
        trip_request_id=payload.trip_request_id,
        threshold_percent=payload.threshold_percent,
        is_active=True,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


@router.get("/alerts", response_model=list[PriceAlertRead])
def list_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PriceAlert]:
    return list(
        db.scalars(
            select(PriceAlert)
            .where(PriceAlert.user_id == current_user.id)
            .order_by(PriceAlert.created_at.desc())
        )
    )

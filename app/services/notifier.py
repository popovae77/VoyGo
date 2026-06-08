from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.notification import Notification
from app.models.user import User
from app.services.email_sender import send_email


class NotifierService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()

    def create_in_app(self, user_id: int, message: str, trip_request_id: int | None = None) -> Notification:
        notification = Notification(
            user_id=user_id,
            trip_request_id=trip_request_id,
            message=message,
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def send_price_alert_email(self, user: User, message: str, *, destination: str) -> bool:
        subject = f"{self.settings.app_name}: цена на поездку в {destination} снизилась"
        body = (
            f"Здравствуйте{', ' + user.full_name if user.full_name else ''}!\n\n"
            f"{message}\n\n"
            f"Откройте {self.settings.app_name}, чтобы посмотреть актуальные варианты.\n\n"
            f"— {self.settings.app_name}"
        )
        return send_email(to=user.email, subject=subject, body=body)

    def notify_price_drop(
        self,
        user: User,
        *,
        trip_request_id: int,
        message: str,
        destination: str,
    ) -> Notification:
        notification = self.create_in_app(user.id, message, trip_request_id=trip_request_id)
        self.send_price_alert_email(user, message, destination=destination)
        return notification

    def send_email_stub(self, email: str, message: str) -> None:
        send_email(to=email, subject=f"{self.settings.app_name}: уведомление", body=message)

    def send_telegram_stub(self, user_id: int, message: str) -> None:
        print(f"[telegram-stub] user={user_id}: {message}")

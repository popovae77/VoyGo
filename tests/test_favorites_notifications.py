from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.notification import Notification
from app.services.price_monitor import PriceMonitorService
from app.services.pricing_provider import MockPricingProvider
from app.models.user import User


def auth_headers(client):
    client.post("/api/v1/auth/register", json={"email": "fav@example.com", "password": "secret123"})
    login = client.post("/api/v1/auth/login", json={"email": "fav@example.com", "password": "secret123"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def create_trip(client, headers):
    start = date.today() + timedelta(days=30)
    end = start + timedelta(days=6)
    response = client.post(
        "/api/v1/trips/search",
        headers=headers,
        json={
            "destination": "Казань",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "people_count": 2,
            "budget": "150000",
            "travel_type": "city",
            "comfort_level": "standard",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_favorites_crud(client):
    headers = auth_headers(client)
    data = create_trip(client, headers)
    offer_id = data["offers"][0]["id"]

    create = client.post(f"/api/v1/favorites/{offer_id}", headers=headers)
    assert create.status_code == 201

    listing = client.get("/api/v1/favorites", headers=headers)
    assert listing.status_code == 200
    assert listing.json()[0]["offer_id"] == offer_id

    delete = client.delete(f"/api/v1/favorites/{offer_id}", headers=headers)
    assert delete.status_code == 204


def test_price_drop_creates_notification(client, monkeypatch):
    headers = auth_headers(client)
    data = create_trip(client, headers)
    request_id = data["request"]["id"]
    emails_sent: list[tuple[str, str, str]] = []

    def fake_send_email(*, to: str, subject: str, body: str) -> bool:
        emails_sent.append((to, subject, body))
        return True

    monkeypatch.setattr("app.services.notifier.send_email", fake_send_email)

    alert = client.post("/api/v1/alerts", headers=headers, json={"trip_request_id": request_id, "threshold_percent": 5})
    assert alert.status_code == 201

    db = SessionLocal()
    try:
        created = PriceMonitorService(db, MockPricingProvider(discount_factor=Decimal("0.50"))).check_price_alerts()
        assert created == 1
        notification = db.scalar(select(Notification).where(Notification.trip_request_id == request_id))
        assert notification is not None
        assert "снизилась" in notification.message
        user = db.scalar(select(User).where(User.email == "fav@example.com"))
        assert user is not None
        assert len(emails_sent) == 1
        assert emails_sent[0][0] == user.email
        assert "Voyago" in emails_sent[0][1]
        assert "снизилась" in emails_sent[0][2]
    finally:
        db.close()

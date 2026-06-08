from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TripRequest(Base):
    __tablename__ = "trip_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    origin: Mapped[str] = mapped_column(String(255), nullable=False, default="Москва", server_default="Москва")
    destination: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    people_count: Mapped[int] = mapped_column(Integer, nullable=False)
    budget: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    travel_type: Mapped[str] = mapped_column(String(32), nullable=False)
    comfort_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="trip_requests")
    offers = relationship("TripOffer", back_populates="trip_request", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="trip_request")
    price_alerts = relationship("PriceAlert", back_populates="trip_request", cascade="all, delete-orphan")


class TripOffer(Base):
    __tablename__ = "trip_offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trip_request_id: Mapped[int] = mapped_column(ForeignKey("trip_requests.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    fits_budget: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    breakdown_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    source: Mapped[str] = mapped_column(String(64), default="mock", nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    trip_request = relationship("TripRequest", back_populates="offers")
    favorites = relationship("Favorite", back_populates="offer", cascade="all, delete-orphan")


class TravelTypeCoefficient(Base):
    __tablename__ = "travel_type_coefficients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    travel_type: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    transport_coeff: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=Decimal("1.00"))
    activities_coeff: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=Decimal("1.00"))
    food_coeff: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=Decimal("1.00"))

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    trip_request_id: int | None
    message: str
    is_read: bool
    sent_at: datetime


class PriceAlertCreate(BaseModel):
    trip_request_id: int
    threshold_percent: int = Field(default=5, ge=1, le=90)


class PriceAlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    trip_request_id: int
    threshold_percent: int
    is_active: bool
    created_at: datetime

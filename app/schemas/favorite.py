from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.trip import TripOfferRead


class FavoriteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    offer_id: int
    created_at: datetime
    offer: TripOfferRead

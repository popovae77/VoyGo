from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.favorite import Favorite
from app.models.trip import TripOffer, TripRequest
from app.models.user import User
from app.schemas.favorite import FavoriteRead


router = APIRouter(prefix="/favorites", tags=["Favorites"])


@router.post("/{offer_id}", response_model=FavoriteRead, status_code=status.HTTP_201_CREATED)
def add_favorite(
    offer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Favorite:
    offer = db.scalar(
        select(TripOffer)
        .join(TripRequest)
        .where(TripOffer.id == offer_id, TripRequest.user_id == current_user.id)
    )
    if offer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Вариант поездки не найден")
    existing = db.scalar(
        select(Favorite).where(Favorite.user_id == current_user.id, Favorite.offer_id == offer_id)
    )
    if existing is not None:
        return _get_favorite(db, current_user.id, offer_id)
    favorite = Favorite(user_id=current_user.id, offer_id=offer_id)
    db.add(favorite)
    db.commit()
    return _get_favorite(db, current_user.id, offer_id)


@router.get("", response_model=list[FavoriteRead])
def list_favorites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Favorite]:
    return list(
        db.scalars(
            select(Favorite)
            .options(joinedload(Favorite.offer))
            .where(Favorite.user_id == current_user.id)
            .order_by(Favorite.created_at.desc())
        )
    )


@router.delete("/{offer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_favorite(
    offer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    favorite = db.scalar(
        select(Favorite).where(Favorite.user_id == current_user.id, Favorite.offer_id == offer_id)
    )
    if favorite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Избранное не найдено")
    db.delete(favorite)
    db.commit()


def _get_favorite(db: Session, user_id: int, offer_id: int) -> Favorite:
    favorite = db.scalar(
        select(Favorite)
        .options(joinedload(Favorite.offer))
        .where(Favorite.user_id == user_id, Favorite.offer_id == offer_id)
    )
    if favorite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Избранное не найдено")
    return favorite

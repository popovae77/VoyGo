from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import (
    ForgotPasswordRequest,
    MessageResponse,
    RegisterResponse,
    ResetPasswordRequest,
    Token,
    UserCreate,
    UserLogin,
    UserRead,
)
from app.services.auth_email import send_password_reset_email, send_welcome_email
from app.services.password_reset import (
    create_password_reset_token,
    get_valid_reset_token,
    mark_reset_token_used,
)


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> RegisterResponse:
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email уже зарегистрирован")
    user = User(
        email=payload.email.lower(),
        password_hash=get_password_hash(payload.password),
        full_name=payload.full_name,
        currency=payload.currency.upper(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    welcome_email_sent = send_welcome_email(to=user.email, full_name=user.full_name)
    return RegisterResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        currency=user.currency,
        created_at=user.created_at,
        welcome_email_sent=welcome_email_sent,
    )


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> Token:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")
    return Token(access_token=create_access_token(user.id))


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)) -> MessageResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    email_sent = False
    if user is not None:
        raw_token = create_password_reset_token(db, user)
        email_sent = send_password_reset_email(to=user.email, reset_token=raw_token)
    return MessageResponse(
        message="Если аккаунт с этим email существует, мы отправили ссылку для сброса пароля.",
        email_sent=email_sent,
    )


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> MessageResponse:
    row = get_valid_reset_token(db, payload.token.strip())
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ссылка недействительна или устарела. Запросите сброс пароля снова.",
        )
    user = db.get(User, row.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь не найден")
    user.password_hash = get_password_hash(payload.new_password)
    mark_reset_token_used(row)
    db.commit()
    return MessageResponse(message="Пароль обновлён. Теперь можно войти с новым паролем.")


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user

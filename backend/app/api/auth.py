from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest
from backend.app.services.auth_service import (
    create_access_token,
    create_user,
    get_user_by_email,
    verify_password,
)


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    try:
        existing_user = get_user_by_email(db, request.email)
    except SQLAlchemyError as exc:
        raise _database_unavailable_error() from exc

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu e-posta adresi zaten kayitli.",
        )

    try:
        user = create_user(db, request.email, request.password)
    except SQLAlchemyError as exc:
        raise _database_unavailable_error() from exc

    return AuthResponse(
        access_token=create_access_token(user.email),
        email=user.email,
    )


@router.post("/login", response_model=AuthResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    try:
        user = get_user_by_email(db, request.email)
    except SQLAlchemyError as exc:
        raise _database_unavailable_error() from exc

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-posta veya sifre hatali.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kullanici hesabi aktif degil.",
        )

    return AuthResponse(
        access_token=create_access_token(user.email),
        email=user.email,
    )


def _database_unavailable_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Veritabani su anda kullanilamiyor.",
    )

import logging
import uuid
from typing import Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    oauth2_scheme,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import Token, UserRegisterRequest

logger = logging.getLogger(__name__)


class AuthService:
    """Service handling user registration, authentication, and JWT lifecycle."""

    @staticmethod
    def register_user(db: Session, user_in: UserRegisterRequest) -> User:
        """Register a new user after verifying that the email is unique.

        Raises:
            HTTPException(409): If the email is already registered.
            HTTPException(500): If a database transaction error occurs.
        """
        normalized_email = user_in.email.lower().strip()

        # Check for duplicate email
        existing_user = db.query(User).filter(User.email == normalized_email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An account with email '{normalized_email}' already exists.",
            )

        # Hash password securely using bcrypt
        password_hash = hash_password(user_in.password)

        new_user = User(
            email=normalized_email,
            password_hash=password_hash,
        )

        try:
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            logger.info("Successfully registered new user: %s (id=%s)", normalized_email, new_user.id)
            return new_user
        except SQLAlchemyError as exc:
            db.rollback()
            logger.error("Failed to commit new user '%s': %s", normalized_email, exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred while creating user account.",
            )

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> User:
        """Validate email and password credentials.

        Raises:
            HTTPException(401): If email is not found or password does not match.
        """
        normalized_email = email.lower().strip()
        user = db.query(User).filter(User.email == normalized_email).first()

        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    @staticmethod
    def create_user_token(user: User) -> Token:
        """Generate a standard OAuth2 Token object containing a signed JWT."""
        expires_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        access_token = create_access_token(
            subject=str(user.id),
            extra_claims={"email": user.email},
        )
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_seconds,
        )

    @staticmethod
    def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db),
    ) -> User:
        """FastAPI dependency to extract and authenticate the user from Bearer JWT.

        Raises:
            HTTPException(401): If token is missing, expired, invalid, or user not found.
        """
        payload = decode_access_token(token)
        user_id_str: Optional[str] = payload.get("sub")

        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials: token missing subject identifier.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            user_uuid = uuid.UUID(user_id_str)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials: invalid user ID format.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = db.query(User).filter(User.id == user_uuid).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account associated with this token no longer exists.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

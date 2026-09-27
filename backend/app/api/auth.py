import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import Token, UserRegisterRequest, UserResponse
from app.services.auth import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    responses={
        201: {"description": "User account successfully created"},
        400: {"description": "Invalid input data or email validation failure"},
        409: {"description": "An account with this email address already exists"},
        500: {"description": "Internal database error"},
    },
)
def register(
    user_in: UserRegisterRequest,
    db: Session = Depends(get_db),
):
    """Register a new user with email and password.

    - **email**: Valid and unique email address.
    - **password**: Secure plaintext password (min 8 characters).
    """
    new_user = AuthService.register_user(db, user_in)
    return new_user


@router.post(
    "/login",
    response_model=Token,
    summary="Authenticate user and issue JWT access token",
    responses={
        200: {"description": "Authentication successful, returns JWT bearer access token"},
        401: {"description": "Invalid email or password credentials"},
        422: {"description": "Missing credentials in request body"},
    },
    openapi_extra={
        "requestBody": {
            "content": {
                "application/x-www-form-urlencoded": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "username": {"type": "string", "description": "Account email address"},
                            "password": {"type": "string", "description": "Account password"},
                        },
                        "required": ["username", "password"],
                    }
                },
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "email": {"type": "string", "description": "Account email address"},
                            "password": {"type": "string", "description": "Account password"},
                        },
                        "required": ["email", "password"],
                    }
                },
            }
        }
    },
)
async def login(
    request: Request,
    db: Session = Depends(get_db),
):
    """Authenticate via OAuth2 Password Flow or JSON payload.

    Accepts:
    - **OAuth2 Form**: `application/x-www-form-urlencoded` with fields `username` (email) and `password`.
    - **JSON**: `application/json` with fields `email` (or `username`) and `password`.
    """
    content_type = request.headers.get("content-type", "").lower()

    if "application/json" in content_type:
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Malformed JSON in request body.",
            )
        email = body.get("email") or body.get("username")
        password = body.get("password")
    else:
        try:
            form = await request.form()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Malformed form data in request body.",
            )
        email = form.get("username") or form.get("email")
        password = form.get("password")

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Both 'email'/'username' and 'password' are required for authentication.",
        )

    user = AuthService.authenticate_user(db, email=str(email), password=str(password))
    return AuthService.create_user_token(user)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile",
    responses={
        200: {"description": "Profile of authenticated user"},
        401: {"description": "Missing, invalid, or expired JWT bearer token"},
    },
)
def get_me(
    current_user: User = Depends(AuthService.get_current_user),
):
    """Retrieve profile information for the currently authenticated user.

    Requires an `Authorization: Bearer <token>` header.
    """
    return current_user

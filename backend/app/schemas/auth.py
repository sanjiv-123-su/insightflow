import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegisterRequest(BaseModel):
    """Payload schema for new user registration."""
    email: EmailStr = Field(..., description="User's unique email address", examples=["user@insightflow.io"])
    password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="Plaintext password (min 8 characters, max 72 characters due to bcrypt limit)",
        examples=["SecurePass123!"],
    )


class UserLoginRequest(BaseModel):
    """Payload schema for JSON-based user login."""
    email: EmailStr = Field(..., description="Registered email address", examples=["user@insightflow.io"])
    password: str = Field(..., min_length=1, description="Account password", examples=["SecurePass123!"])


class Token(BaseModel):
    """Standard OAuth2 token response schema."""
    access_token: str = Field(..., description="Signed JWT access token string")
    token_type: str = Field(default="bearer", description="Token scheme type, default bearer")
    expires_in: int = Field(..., description="Token validity duration in seconds")


class TokenPayload(BaseModel):
    """Internal decoded JWT token payload representation."""
    sub: Optional[str] = None
    email: Optional[str] = None
    exp: Optional[int] = None


class UserResponse(BaseModel):
    """Public user profile response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    created_at: datetime

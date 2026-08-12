"""Pydantic schemas for authentication and user management."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Payload for POST /api/v1/auth/login."""
    email: EmailStr = Field(..., json_schema_extra={"example": "employee@company.com"})
    password: str = Field(..., min_length=6, json_schema_extra={"example": "Password123!"})


class TokenResponse(BaseModel):
    """Response payload returned upon successful authentication."""
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    email: str
    role: str
    expires_in_seconds: int


class UserResponse(BaseModel):
    """User profile details payload."""
    id: UUID
    email: EmailStr
    name: str
    role: str  # e.g., "employee" or "admin"
    department: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

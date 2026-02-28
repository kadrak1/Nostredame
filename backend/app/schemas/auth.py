"""Pydantic schemas for authentication endpoints."""

from pydantic import BaseModel, Field

from app.models.enums import UserRole


# --- Request ---

class LoginRequest(BaseModel):
    login: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=200)


# --- Response ---

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    venue_id: int
    login: str
    role: UserRole
    display_name: str

    model_config = {"from_attributes": True}

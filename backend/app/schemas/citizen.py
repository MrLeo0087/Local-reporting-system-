import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class CitizenLogin(BaseModel):
    email: EmailStr
    password: str


class CitizenOut(BaseModel):
    """
    Public-facing citizen shape. Deliberately excludes fake_report_count and
    report_locked_until — those must never appear in citizen-facing responses.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: EmailStr
    phone: str
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class CitizenUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, min_length=6, max_length=20)
    password: Optional[str] = Field(default=None, min_length=8, max_length=100)


class CitizenAdminOut(BaseModel):
    """Admin-only view of a citizen — includes fields CitizenOut deliberately hides."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: EmailStr
    phone: str
    citizenship_number: Optional[str] = None
    has_citizenship_photo: bool
    disabled: bool
    created_at: datetime

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator

from app.models.staff import STAFF_ROLES, STAFF_CATEGORIES


class StaffLogin(BaseModel):
    email: EmailStr
    password: str


class StaffCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    role: str
    category: Optional[str] = None
    ward_no: Optional[int] = None

    @model_validator(mode="after")
    def validate_role_specific_fields(self):
        if self.role not in STAFF_ROLES:
            raise ValueError(f"role must be one of {STAFF_ROLES}")

        if self.role == "staff":
            if self.category not in STAFF_CATEGORIES:
                raise ValueError(f"category must be one of {STAFF_CATEGORIES}")
            if self.ward_no is None:
                raise ValueError("ward_no is required for staff accounts")
        return self


class StaffOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: EmailStr
    role: str
    category: Optional[str] = None
    ward_no: Optional[int] = None
    disabled: bool
    created_at: datetime

import uuid

from sqlalchemy import Column, String, Integer, Boolean, TIMESTAMP, CheckConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base

STAFF_ROLES = ("staff", "admin")
STAFF_CATEGORIES = ("road", "electric", "water_supply", "public_property", "other")


class Staff(Base):
    __tablename__ = "staff"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String(20), nullable=False)
    category = Column(String(30), nullable=True)  # nullable for admin
    ward_no = Column(Integer, nullable=True)  # nullable for admin
    disabled = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(f"role IN {STAFF_ROLES}", name="staff_role_check"),
        CheckConstraint(
            f"category IS NULL OR category IN {STAFF_CATEGORIES}", name="staff_category_check"
        ),
    )

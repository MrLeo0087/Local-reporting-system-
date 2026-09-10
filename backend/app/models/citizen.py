import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, Boolean, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Citizen(Base):
    __tablename__ = "citizens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=False)
    password_hash = Column(String, nullable=False)

    # Fake-report lockout bookkeeping. Never exposed in citizen-facing responses.
    fake_report_count = Column(Integer, nullable=False, default=0)
    report_locked_until = Column(TIMESTAMP(timezone=True), nullable=True)

    # Permanent disable, set manually by an admin. Separate from the 7-day auto lock.
    disabled = Column(Boolean, nullable=False, default=False)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    reports = relationship("Report", back_populates="citizen")

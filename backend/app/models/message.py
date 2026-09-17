import uuid

from sqlalchemy import Column, Text, TIMESTAMP, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Message(Base):
    """
    A single message in the conversation attached to one report. Exactly one
    of citizen_id/staff_id is set, identifying who sent it — the citizen who
    filed the report, or a staff member from the assigned category/ward.
    """
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id"), nullable=False, index=True)
    citizen_id = Column(UUID(as_uuid=True), ForeignKey("citizens.id"), nullable=True)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("staff.id"), nullable=True)

    body = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    report = relationship("Report", back_populates="messages")
    citizen = relationship("Citizen")
    staff = relationship("Staff")

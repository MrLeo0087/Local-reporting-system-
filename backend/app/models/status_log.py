import uuid

from sqlalchemy import Column, String, Text, TIMESTAMP, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class StatusLog(Base):
    __tablename__ = "status_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id"), nullable=False)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("staff.id"), nullable=True)

    action = Column(String(30), nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    report = relationship("Report", back_populates="status_logs")
    staff = relationship("Staff")

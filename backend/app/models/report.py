import uuid

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    Text,
    Date,
    TIMESTAMP,
    ForeignKey,
    CheckConstraint,
    LargeBinary,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.staff import STAFF_CATEGORIES

REPORT_STATUSES = ("submitted", "verified", "rejected", "in_progress", "completed")
REJECTION_REASONS = ("duplicate", "not_enough_info", "false_report")


class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    citizen_id = Column(UUID(as_uuid=True), ForeignKey("citizens.id"), nullable=False)

    category = Column(String(30), nullable=False)
    ward_no = Column(Integer, nullable=False)
    landmark = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)

    # Legacy field, kept for old rows — no longer used to serve photos (Render's
    # free-tier disk is wiped on every restart, so files written there don't
    # survive). New uploads instead go straight into the database below.
    photo_path = Column(Text, nullable=False)
    photo_data = Column(LargeBinary, nullable=True)
    photo_content_type = Column(String(50), nullable=True)

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    display_publicly = Column(Boolean, nullable=False, default=True)

    status = Column(String(20), nullable=False, default="submitted")
    rejection_reason = Column(String(30), nullable=True)
    expected_completion_date = Column(Date, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    citizen = relationship("Citizen", back_populates="reports")
    status_logs = relationship(
        "StatusLog", back_populates="report", order_by="StatusLog.created_at"
    )
    messages = relationship(
        "Message", back_populates="report", order_by="Message.created_at"
    )

    @property
    def photo_url(self) -> str:
        """Where the frontend fetches this report's photo from (see GET /reports/{id}/photo)."""
        return f"/reports/{self.id}/photo"

    __table_args__ = (
        CheckConstraint(f"category IN {STAFF_CATEGORIES}", name="report_category_check"),
        CheckConstraint(f"status IN {REPORT_STATUSES}", name="report_status_check"),
        CheckConstraint(
            f"rejection_reason IS NULL OR rejection_reason IN {REJECTION_REASONS}",
            name="report_rejection_reason_check",
        ),
    )

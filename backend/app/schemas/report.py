import uuid
from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from app.models.report import REJECTION_REASONS


class StatusLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    action: str
    comment: Optional[str] = None
    created_at: datetime


class ReportOut(BaseModel):
    """
    Public/citizen-facing report shape. reporter_name is filled in by the
    router: either the citizen's real name, or "Anonymous Citizen" if
    display_publicly is False (public feed only — staff/admin always get
    the real name via ReportStaffOut instead).
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: str
    ward_no: int
    landmark: str
    description: str
    photo_path: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    status: str
    rejection_reason: Optional[str] = None
    expected_completion_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime
    reporter_name: str


class ReportDetailOut(ReportOut):
    status_logs: list[StatusLogOut] = []


class ReportStaffOut(ReportOut):
    """Same as ReportOut but always carries the real citizen identity."""
    citizen_email: str
    citizen_phone: str


class RejectReportIn(BaseModel):
    reason: str
    comment: Optional[str] = None

    def validate_reason(self):
        if self.reason not in REJECTION_REASONS:
            raise ValueError(f"reason must be one of {REJECTION_REASONS}")


class ProgressReportIn(BaseModel):
    expected_completion_date: date
    comment: Optional[str] = None


class SimpleActionIn(BaseModel):
    comment: Optional[str] = None

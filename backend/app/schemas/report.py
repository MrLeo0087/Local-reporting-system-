import uuid
from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict, model_validator

from app.models.report import REJECTION_REASONS
from app.models.staff import STAFF_CATEGORIES


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


class ReportAdminOut(ReportStaffOut):
    """Admin management view — same fields staff see, for the admin's report-editing table."""


class ReportAdminUpdate(BaseModel):
    category: Optional[str] = None
    ward_no: Optional[int] = None
    landmark: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_category(self):
        if self.category is not None and self.category not in STAFF_CATEGORIES:
            raise ValueError(f"category must be one of {STAFF_CATEGORIES}")
        return self


class UnassignedReportOut(BaseModel):
    """
    Admin-only, read-only: a report with no active staff member matching its
    category+ward, so nobody currently sees it in a staff dashboard. Lets
    admin notice and close the gap by creating the right staff account —
    admin still can't act on the report itself (see require_staff_only).
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: str
    ward_no: int
    landmark: str
    status: str
    created_at: datetime

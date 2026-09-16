import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.staff import Staff
from app.models.citizen import Citizen
from app.models.report import Report, REJECTION_REASONS
from app.models.status_log import StatusLog
from app.schemas.staff import StaffLogin
from app.schemas.citizen import TokenOut
from app.schemas.report import (
    ReportStaffOut,
    RejectReportIn,
    ProgressReportIn,
    SimpleActionIn,
)
from app.auth.security import verify_password, create_access_token
from app.auth.dependencies import require_staff_only
from app.utils.fake_report_lock import register_false_report

router = APIRouter(prefix="/staff", tags=["staff"])


def _to_staff_report_out(report: Report) -> ReportStaffOut:
    reporter_name = report.citizen.full_name  # staff always see the real name
    return ReportStaffOut(
        id=report.id,
        category=report.category,
        ward_no=report.ward_no,
        landmark=report.landmark,
        description=report.description,
        photo_path=report.photo_url,
        latitude=report.latitude,
        longitude=report.longitude,
        status=report.status,
        rejection_reason=report.rejection_reason,
        expected_completion_date=report.expected_completion_date,
        created_at=report.created_at,
        updated_at=report.updated_at,
        reporter_name=reporter_name,
        citizen_email=report.citizen.email,
        citizen_phone=report.citizen.phone,
    )


@router.post("/login", response_model=TokenOut)
def login(payload: StaffLogin, db: Session = Depends(get_db)):
    staff = db.query(Staff).filter(Staff.email == payload.email).first()
    if not staff or not verify_password(payload.password, staff.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    if staff.disabled:
        raise HTTPException(status_code=403, detail="This account has been disabled.")

    token = create_access_token(
        {
            "sub": str(staff.id),
            "role": staff.role,
            "category": staff.category,
            "ward_no": staff.ward_no,
        }
    )
    return TokenOut(access_token=token, role=staff.role)


def _get_report_for_staff(report_id: uuid.UUID, db: Session, staff: Staff) -> Report:
    report = (
        db.query(Report)
        .options(joinedload(Report.citizen))
        .filter(Report.id == report_id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    # Staff only act on reports in their own assigned category + ward
    if report.category != staff.category or report.ward_no != staff.ward_no:
        raise HTTPException(
            status_code=403,
            detail="This report is outside your assigned category/ward.",
        )
    return report


@router.get("/reports", response_model=list[ReportStaffOut])
def staff_reports(db: Session = Depends(get_db), staff: Staff = Depends(require_staff_only)):
    reports = (
        db.query(Report)
        .options(joinedload(Report.citizen))
        .filter(Report.category == staff.category, Report.ward_no == staff.ward_no)
        .order_by(Report.created_at.desc())
        .all()
    )
    return [_to_staff_report_out(r) for r in reports]


@router.patch("/reports/{report_id}/verify", response_model=ReportStaffOut)
def verify_report(
    report_id: uuid.UUID,
    payload: SimpleActionIn = SimpleActionIn(),
    db: Session = Depends(get_db),
    staff: Staff = Depends(require_staff_only),
):
    report = _get_report_for_staff(report_id, db, staff)

    report.status = "verified"
    db.add(report)
    db.add(StatusLog(report_id=report.id, staff_id=staff.id, action="verified", comment=payload.comment))
    db.commit()
    db.refresh(report)
    return _to_staff_report_out(report)


@router.patch("/reports/{report_id}/reject", response_model=ReportStaffOut)
def reject_report(
    report_id: uuid.UUID,
    payload: RejectReportIn,
    db: Session = Depends(get_db),
    staff: Staff = Depends(require_staff_only),
):
    if payload.reason not in REJECTION_REASONS:
        raise HTTPException(status_code=400, detail=f"reason must be one of {REJECTION_REASONS}")

    report = _get_report_for_staff(report_id, db, staff)

    report.status = "rejected"
    report.rejection_reason = payload.reason
    db.add(report)
    db.add(
        StatusLog(
            report_id=report.id, staff_id=staff.id, action="rejected", comment=payload.comment
        )
    )

    if payload.reason == "false_report":
        citizen = db.query(Citizen).filter(Citizen.id == report.citizen_id).first()
        # Flush first so the just-added status log's timestamp is visible to
        # the lockout check's query over status_logs.
        db.flush()
        register_false_report(db, citizen)

    db.commit()
    db.refresh(report)
    return _to_staff_report_out(report)


@router.patch("/reports/{report_id}/progress", response_model=ReportStaffOut)
def progress_report(
    report_id: uuid.UUID,
    payload: ProgressReportIn,
    db: Session = Depends(get_db),
    staff: Staff = Depends(require_staff_only),
):
    report = _get_report_for_staff(report_id, db, staff)

    report.status = "in_progress"
    report.expected_completion_date = payload.expected_completion_date
    db.add(report)
    db.add(
        StatusLog(
            report_id=report.id, staff_id=staff.id, action="in_progress", comment=payload.comment
        )
    )
    db.commit()
    db.refresh(report)
    return _to_staff_report_out(report)


@router.patch("/reports/{report_id}/complete", response_model=ReportStaffOut)
def complete_report(
    report_id: uuid.UUID,
    payload: SimpleActionIn = SimpleActionIn(),
    db: Session = Depends(get_db),
    staff: Staff = Depends(require_staff_only),
):
    report = _get_report_for_staff(report_id, db, staff)

    report.status = "completed"
    db.add(report)
    db.add(
        StatusLog(report_id=report.id, staff_id=staff.id, action="completed", comment=payload.comment)
    )
    db.commit()
    db.refresh(report)
    return _to_staff_report_out(report)

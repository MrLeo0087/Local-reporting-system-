import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.models.citizen import Citizen
from app.models.report import Report, REPORT_STATUSES
from app.models.status_log import StatusLog
from app.models.message import Message
from app.models.staff import STAFF_CATEGORIES
from app.schemas.report import ReportOut, ReportDetailOut, ReportAdminUpdate
from app.auth.dependencies import get_current_citizen, get_optional_actor
from app.utils.uploads import process_report_photo
from app.utils.fake_report_lock import check_not_locked

router = APIRouter(tags=["reports"])


def _reporter_name(report: Report) -> str:
    if report.display_publicly:
        return report.citizen.full_name
    return "Anonymous Citizen"


def _to_report_out(report: Report) -> ReportOut:
    return ReportOut(
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
        reporter_name=_reporter_name(report),
    )


@router.post("/reports", response_model=ReportOut, status_code=201)
def submit_report(
    category: str = Form(...),
    ward_no: int = Form(...),
    landmark: str = Form(..., max_length=200),
    description: str = Form(...),
    display_publicly: bool = Form(True),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    citizen: Citizen = Depends(get_current_citizen),
):
    if category not in STAFF_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"category must be one of {STAFF_CATEGORIES}")
    if not landmark.strip() or not description.strip():
        raise HTTPException(status_code=400, detail="landmark and description are required.")

    try:
        check_not_locked(citizen)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    photo_bytes, photo_content_type, filename = process_report_photo(photo)

    report = Report(
        citizen_id=citizen.id,
        category=category,
        ward_no=ward_no,
        landmark=landmark.strip(),
        description=description.strip(),
        photo_path=filename,
        photo_data=photo_bytes,
        photo_content_type=photo_content_type,
        latitude=latitude,
        longitude=longitude,
        display_publicly=display_publicly,
        status="submitted",
    )
    db.add(report)
    db.flush()  # get report.id before commit

    log = StatusLog(report_id=report.id, staff_id=None, action="submitted", comment=None)
    db.add(log)

    db.commit()
    db.refresh(report)
    return _to_report_out(report)


@router.get("/reports/{report_id}/photo")
def report_photo(report_id: uuid.UUID, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    if report.photo_data:
        return Response(content=report.photo_data, media_type=report.photo_content_type or "image/jpeg")

    # Legacy fallback for reports uploaded before photos moved into the
    # database — only works if the file still happens to exist on local
    # disk (won't be true on Render after a restart).
    legacy_file = os.path.join(settings.upload_dir, os.path.basename(report.photo_path or ""))
    if os.path.isfile(legacy_file):
        with open(legacy_file, "rb") as f:
            data = f.read()
        ext = os.path.splitext(legacy_file)[1].lower()
        media_type = "image/png" if ext == ".png" else "image/jpeg"
        return Response(content=data, media_type=media_type)

    raise HTTPException(status_code=404, detail="Photo not available for this report.")


@router.get("/reports", response_model=list[ReportOut])
def public_feed(
    category: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Report).options(joinedload(Report.citizen)).order_by(Report.created_at.desc())

    if category:
        if category not in STAFF_CATEGORIES:
            raise HTTPException(status_code=400, detail=f"category must be one of {STAFF_CATEGORIES}")
        query = query.filter(Report.category == category)

    if status_filter:
        if status_filter not in REPORT_STATUSES:
            raise HTTPException(status_code=400, detail=f"status must be one of {REPORT_STATUSES}")
        query = query.filter(Report.status == status_filter)

    reports = query.all()
    return [_to_report_out(r) for r in reports]


@router.get("/reports/mine", response_model=list[ReportOut])
def my_reports(
    db: Session = Depends(get_db),
    citizen: Citizen = Depends(get_current_citizen),
):
    reports = (
        db.query(Report)
        .options(joinedload(Report.citizen))
        .filter(Report.citizen_id == citizen.id)
        .order_by(Report.created_at.desc())
        .all()
    )
    return [_to_report_out(r) for r in reports]


@router.patch("/reports/{report_id}", response_model=ReportOut)
def update_my_report(
    report_id: uuid.UUID,
    payload: ReportAdminUpdate,
    db: Session = Depends(get_db),
    citizen: Citizen = Depends(get_current_citizen),
):
    report = (
        db.query(Report)
        .options(joinedload(Report.citizen))
        .filter(Report.id == report_id, Report.citizen_id == citizen.id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    # Editing is only safe while staff haven't acted on it yet — once
    # verified/rejected/etc, staff have already read and started acting on
    # what was submitted, so changing it out from under them isn't allowed.
    if report.status != "submitted":
        raise HTTPException(
            status_code=400,
            detail="This report has already been reviewed by the department and can no longer be edited.",
        )

    if payload.category is not None:
        report.category = payload.category
    if payload.ward_no is not None:
        report.ward_no = payload.ward_no
    if payload.landmark is not None:
        report.landmark = payload.landmark
    if payload.description is not None:
        report.description = payload.description

    db.add(report)
    db.commit()
    db.refresh(report)
    return _to_report_out(report)


@router.delete("/reports/{report_id}", status_code=204)
def delete_my_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    citizen: Citizen = Depends(get_current_citizen),
):
    report = db.query(Report).filter(Report.id == report_id, Report.citizen_id == citizen.id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    if report.status != "submitted":
        raise HTTPException(
            status_code=400,
            detail="This report has already been reviewed by the department and can no longer be deleted.",
        )

    db.query(Message).filter(Message.report_id == report_id).delete(synchronize_session=False)
    db.query(StatusLog).filter(StatusLog.report_id == report_id).delete(synchronize_session=False)
    db.delete(report)
    db.commit()
    return Response(status_code=204)


@router.get("/reports/{report_id}", response_model=ReportDetailOut)
def report_detail(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: Optional[tuple] = Depends(get_optional_actor),
):
    report = (
        db.query(Report)
        .options(joinedload(Report.citizen), joinedload(Report.status_logs))
        .filter(Report.id == report_id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    # "Anonymous" is a public-feed courtesy toward other citizens, not a
    # shield from staff or the reporter's own view of their own report —
    # staff need the real identity to act responsibly (and to stop the
    # anonymity option being abused to submit bad-faith reports consequence-free).
    reveal_real_name = False
    if actor:
        kind, user = actor
        if kind == "staff":
            reveal_real_name = True
        elif kind == "citizen" and user.id == report.citizen_id:
            reveal_real_name = True

    base = _to_report_out(report)
    if reveal_real_name:
        base.reporter_name = report.citizen.full_name
    return ReportDetailOut(**base.model_dump(), status_logs=report.status_logs)

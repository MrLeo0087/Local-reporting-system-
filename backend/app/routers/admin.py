import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.staff import Staff
from app.models.citizen import Citizen
from app.models.report import Report
from app.models.status_log import StatusLog
from app.models.message import Message
from app.schemas.staff import StaffCreate, StaffOut, StaffUpdate
from app.schemas.citizen import CitizenAdminOut, CitizenUpdate
from app.schemas.report import UnassignedReportOut, ReportAdminOut, ReportAdminUpdate
from app.auth.security import hash_password
from app.auth.dependencies import require_admin

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/staff", response_model=StaffOut, status_code=201)
def create_staff(
    payload: StaffCreate,
    db: Session = Depends(get_db),
    _admin: Staff = Depends(require_admin),
):
    existing = db.query(Staff).filter(Staff.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="A staff account with this email already exists.")

    staff = Staff(
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        category=payload.category if payload.role == "staff" else None,
        ward_no=payload.ward_no if payload.role == "staff" else None,
    )
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return staff


@router.get("/staff", response_model=list[StaffOut])
def list_staff(db: Session = Depends(get_db), _admin: Staff = Depends(require_admin)):
    return db.query(Staff).order_by(Staff.created_at.desc()).all()


@router.patch("/staff/{staff_id}/disable", response_model=StaffOut)
def disable_staff(
    staff_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Staff = Depends(require_admin),
):
    if staff_id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot disable your own account.")

    staff = db.query(Staff).filter(Staff.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff account not found.")

    # A "remove" here means disable rather than delete: status_logs.staff_id
    # references this row for every action they've ever taken, so a real
    # DELETE would either fail outright or blow a hole in the audit trail.
    # Disabling blocks login/API use immediately while keeping history intact.
    staff.disabled = True
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return staff


@router.patch("/staff/{staff_id}/enable", response_model=StaffOut)
def enable_staff(
    staff_id: uuid.UUID,
    db: Session = Depends(get_db),
    _admin: Staff = Depends(require_admin),
):
    staff = db.query(Staff).filter(Staff.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff account not found.")

    staff.disabled = False
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return staff


@router.patch("/staff/{staff_id}", response_model=StaffOut)
def update_staff(
    staff_id: uuid.UUID,
    payload: StaffUpdate,
    db: Session = Depends(get_db),
    _admin: Staff = Depends(require_admin),
):
    staff = db.query(Staff).filter(Staff.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff account not found.")

    if payload.email is not None and payload.email != staff.email:
        existing = db.query(Staff).filter(Staff.email == payload.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="A staff account with this email already exists.")
        staff.email = payload.email

    if payload.full_name is not None:
        staff.full_name = payload.full_name
    if payload.password is not None:
        staff.password_hash = hash_password(payload.password)

    role = payload.role if payload.role is not None else staff.role
    staff.role = role
    if role == "staff":
        if payload.category is not None:
            staff.category = payload.category
        if payload.ward_no is not None:
            staff.ward_no = payload.ward_no
    else:
        staff.category = None
        staff.ward_no = None

    db.add(staff)
    db.commit()
    db.refresh(staff)
    return staff


@router.delete("/staff/{staff_id}", status_code=204)
def delete_staff(
    staff_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Staff = Depends(require_admin),
):
    if staff_id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account.")

    staff = db.query(Staff).filter(Staff.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff account not found.")

    # Detach this staff member from their past actions rather than deleting
    # those status_log rows too, so the report history stays intact even
    # after the account itself is gone for good.
    db.query(StatusLog).filter(StatusLog.staff_id == staff_id).update({StatusLog.staff_id: None})
    db.delete(staff)
    db.commit()
    return Response(status_code=204)


@router.get("/citizens", response_model=list[CitizenAdminOut])
def list_citizens(db: Session = Depends(get_db), _admin: Staff = Depends(require_admin)):
    return db.query(Citizen).order_by(Citizen.created_at.desc()).all()


@router.patch("/citizens/{citizen_id}/disable", response_model=CitizenAdminOut)
def disable_citizen(
    citizen_id: uuid.UUID,
    db: Session = Depends(get_db),
    _admin: Staff = Depends(require_admin),
):
    citizen = db.query(Citizen).filter(Citizen.id == citizen_id).first()
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found.")

    citizen.disabled = True
    db.add(citizen)
    db.commit()
    db.refresh(citizen)
    return citizen


@router.patch("/citizens/{citizen_id}", response_model=CitizenAdminOut)
def update_citizen(
    citizen_id: uuid.UUID,
    payload: CitizenUpdate,
    db: Session = Depends(get_db),
    _admin: Staff = Depends(require_admin),
):
    citizen = db.query(Citizen).filter(Citizen.id == citizen_id).first()
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found.")

    if payload.email is not None and payload.email != citizen.email:
        existing = db.query(Citizen).filter(Citizen.email == payload.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="A citizen account with this email already exists.")
        citizen.email = payload.email

    if payload.full_name is not None:
        citizen.full_name = payload.full_name
    if payload.phone is not None:
        citizen.phone = payload.phone
    if payload.password is not None:
        citizen.password_hash = hash_password(payload.password)

    db.add(citizen)
    db.commit()
    db.refresh(citizen)
    return citizen


@router.delete("/citizens/{citizen_id}", status_code=204)
def delete_citizen(
    citizen_id: uuid.UUID,
    db: Session = Depends(get_db),
    _admin: Staff = Depends(require_admin),
):
    citizen = db.query(Citizen).filter(Citizen.id == citizen_id).first()
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found.")

    # A citizen's reports carry a required (non-nullable) citizen_id, unlike
    # staff on status_logs, so a real delete has to take their reports (and
    # those reports' status_logs/messages) with it rather than orphaning them.
    report_ids = [r.id for r in db.query(Report.id).filter(Report.citizen_id == citizen_id).all()]
    if report_ids:
        db.query(Message).filter(Message.report_id.in_(report_ids)).delete(synchronize_session=False)
        db.query(StatusLog).filter(StatusLog.report_id.in_(report_ids)).delete(synchronize_session=False)
        db.query(Report).filter(Report.id.in_(report_ids)).delete(synchronize_session=False)

    db.delete(citizen)
    db.commit()
    return Response(status_code=204)


@router.get("/citizens/{citizen_id}/citizenship-photo")
def citizen_citizenship_photo(
    citizen_id: uuid.UUID,
    db: Session = Depends(get_db),
    _admin: Staff = Depends(require_admin),
):
    """
    Admin-only — the citizenship card photo captured at registration, used to
    manually cross-check identity. Never exposed to any other role.
    """
    citizen = db.query(Citizen).filter(Citizen.id == citizen_id).first()
    if not citizen or not citizen.citizenship_photo_data:
        raise HTTPException(status_code=404, detail="No citizenship photo on file.")
    return Response(
        content=citizen.citizenship_photo_data,
        media_type=citizen.citizenship_photo_content_type or "image/jpeg",
    )


@router.patch("/citizens/{citizen_id}/enable", response_model=CitizenAdminOut)
def enable_citizen(
    citizen_id: uuid.UUID,
    db: Session = Depends(get_db),
    _admin: Staff = Depends(require_admin),
):
    citizen = db.query(Citizen).filter(Citizen.id == citizen_id).first()
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found.")

    citizen.disabled = False
    db.add(citizen)
    db.commit()
    db.refresh(citizen)
    return citizen


@router.get("/reports/unassigned", response_model=list[UnassignedReportOut])
def unassigned_reports(db: Session = Depends(get_db), _admin: Staff = Depends(require_admin)):
    """
    Reports with no active (non-disabled) staff member covering their exact
    category+ward — invisible to every staff dashboard until someone is
    assigned there. Read-only: admin still can't verify/reject/etc these.
    """
    active_pairs = set(
        db.query(Staff.category, Staff.ward_no)
        .filter(Staff.role == "staff", Staff.disabled.is_(False))
        .all()
    )
    reports = db.query(Report).order_by(Report.created_at.desc()).all()
    return [r for r in reports if (r.category, r.ward_no) not in active_pairs]


def _to_report_admin_out(report: Report) -> ReportAdminOut:
    return ReportAdminOut(
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
        reporter_name=report.citizen.full_name,
        citizen_email=report.citizen.email,
        citizen_phone=report.citizen.phone,
    )


@router.get("/reports", response_model=list[ReportAdminOut])
def list_all_reports(db: Session = Depends(get_db), _admin: Staff = Depends(require_admin)):
    reports = db.query(Report).order_by(Report.created_at.desc()).all()
    return [_to_report_admin_out(r) for r in reports]


@router.patch("/reports/{report_id}", response_model=ReportAdminOut)
def update_report(
    report_id: uuid.UUID,
    payload: ReportAdminUpdate,
    db: Session = Depends(get_db),
    _admin: Staff = Depends(require_admin),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

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
    return _to_report_admin_out(report)


@router.delete("/reports/{report_id}", status_code=204)
def delete_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    _admin: Staff = Depends(require_admin),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    db.query(Message).filter(Message.report_id == report_id).delete(synchronize_session=False)
    db.query(StatusLog).filter(StatusLog.report_id == report_id).delete(synchronize_session=False)
    db.delete(report)
    db.commit()
    return Response(status_code=204)

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.staff import Staff
from app.models.citizen import Citizen
from app.models.report import Report
from app.schemas.staff import StaffCreate, StaffOut
from app.schemas.citizen import CitizenAdminOut
from app.schemas.report import UnassignedReportOut
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

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.staff import Staff
from app.models.citizen import Citizen
from app.schemas.staff import StaffCreate, StaffOut
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


@router.patch("/citizens/{citizen_id}/disable", response_model=dict)
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
    return {"id": str(citizen.id), "disabled": True}

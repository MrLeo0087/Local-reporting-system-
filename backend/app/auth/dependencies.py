"""
Reusable FastAPI dependencies for protecting routes:
- get_current_citizen
- get_current_staff        (any staff member, including admins)
- require_staff_only       (department staff only — not admins)
- require_admin            (admins only)
- get_current_citizen_or_staff  (either — for the report message thread)
"""
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.security import decode_access_token
from app.models.citizen import Citizen
from app.models.staff import Staff

# tokenUrl is only used to populate the "Authorize" button in /docs
citizen_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="citizens/login", auto_error=False)
staff_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="staff/login", auto_error=False)

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_citizen(
    token: str = Depends(citizen_oauth2_scheme), db: Session = Depends(get_db)
) -> Citizen:
    if not token:
        raise CREDENTIALS_EXCEPTION
    payload = decode_access_token(token)
    if not payload or payload.get("role") != "citizen":
        raise CREDENTIALS_EXCEPTION

    try:
        citizen_id = uuid.UUID(payload.get("sub"))
    except (TypeError, ValueError):
        raise CREDENTIALS_EXCEPTION

    citizen = db.query(Citizen).filter(Citizen.id == citizen_id).first()
    if citizen is None:
        raise CREDENTIALS_EXCEPTION
    if citizen.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="This account has been disabled."
        )
    return citizen


def get_current_staff(
    token: str = Depends(staff_oauth2_scheme), db: Session = Depends(get_db)
) -> Staff:
    if not token:
        raise CREDENTIALS_EXCEPTION
    payload = decode_access_token(token)
    if not payload or payload.get("role") not in ("staff", "admin"):
        raise CREDENTIALS_EXCEPTION

    try:
        staff_id = uuid.UUID(payload.get("sub"))
    except (TypeError, ValueError):
        raise CREDENTIALS_EXCEPTION

    staff = db.query(Staff).filter(Staff.id == staff_id).first()
    if staff is None:
        raise CREDENTIALS_EXCEPTION
    if staff.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="This account has been disabled."
        )
    return staff


def require_staff_only(staff: Staff = Depends(get_current_staff)) -> Staff:
    """
    Reviewing/resolving complaints is department staff's job, not admin's —
    admin only manages staff accounts. Blocks admin tokens from every
    complaint-handling endpoint (reading the queue and acting on reports).
    """
    if staff.role != "staff":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action is for department staff only, not admins.",
        )
    return staff


def require_admin(staff: Staff = Depends(get_current_staff)) -> Staff:
    if staff.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires an admin account.",
        )
    return staff


# Either scheme extracts the bearer token the same way regardless of which
# tokenUrl it was declared with — that field only affects the "Authorize"
# button in /docs, so reusing citizen_oauth2_scheme here is fine.
def get_current_citizen_or_staff(
    token: str = Depends(citizen_oauth2_scheme), db: Session = Depends(get_db)
) -> tuple[str, "Citizen | Staff"]:
    """
    For the report message thread, which either the reporting citizen or the
    assigned staff member may read/post to. Returns ("citizen", Citizen) or
    ("staff", Staff) — the caller still has to check the citizen owns the
    report, or the staff's category/ward matches it.
    """
    if not token:
        raise CREDENTIALS_EXCEPTION
    payload = decode_access_token(token)
    role = payload.get("role") if payload else None
    if role not in ("citizen", "staff", "admin"):
        raise CREDENTIALS_EXCEPTION

    try:
        user_id = uuid.UUID(payload.get("sub"))
    except (TypeError, ValueError):
        raise CREDENTIALS_EXCEPTION

    if role == "citizen":
        citizen = db.query(Citizen).filter(Citizen.id == user_id).first()
        if citizen is None or citizen.disabled:
            raise CREDENTIALS_EXCEPTION
        return ("citizen", citizen)

    staff = db.query(Staff).filter(Staff.id == user_id).first()
    if staff is None or staff.disabled:
        raise CREDENTIALS_EXCEPTION
    return ("staff", staff)

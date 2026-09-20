import re

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import EmailStr
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.citizen import Citizen
from app.schemas.citizen import CitizenLogin, CitizenOut, TokenOut, CitizenUpdate
from app.auth.security import hash_password, verify_password, create_access_token
from app.auth.dependencies import get_current_citizen
from app.utils.uploads import process_report_photo

router = APIRouter(prefix="/citizens", tags=["citizens"])

CITIZENSHIP_NUMBER_PATTERN = re.compile(r"^[0-9A-Za-z/-]{5,50}$")


@router.post("/register", response_model=CitizenOut, status_code=status.HTTP_201_CREATED)
def register(
    full_name: str = Form(..., min_length=2, max_length=150),
    email: EmailStr = Form(...),
    phone: str = Form(..., min_length=6, max_length=20),
    password: str = Form(..., min_length=8, max_length=100),
    citizenship_number: str = Form(..., min_length=5, max_length=50),
    citizenship_photo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    citizenship_number = citizenship_number.strip()
    if not CITIZENSHIP_NUMBER_PATTERN.match(citizenship_number):
        raise HTTPException(
            status_code=400,
            detail="Citizenship number looks invalid — use only letters, numbers, '-' and '/'.",
        )

    if db.query(Citizen).filter(Citizen.email == email).first():
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    if db.query(Citizen).filter(Citizen.citizenship_number == citizenship_number).first():
        raise HTTPException(
            status_code=400,
            detail="An account has already been registered with this citizenship number.",
        )

    photo_bytes, photo_content_type, _ = process_report_photo(citizenship_photo)

    citizen = Citizen(
        full_name=full_name,
        email=email,
        phone=phone,
        password_hash=hash_password(password),
        citizenship_number=citizenship_number,
        citizenship_photo_data=photo_bytes,
        citizenship_photo_content_type=photo_content_type,
    )
    db.add(citizen)
    db.commit()
    db.refresh(citizen)
    return citizen


@router.post("/login", response_model=TokenOut)
def login(payload: CitizenLogin, db: Session = Depends(get_db)):
    citizen = db.query(Citizen).filter(Citizen.email == payload.email).first()
    if not citizen or not verify_password(payload.password, citizen.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    if citizen.disabled:
        raise HTTPException(status_code=403, detail="This account has been disabled.")

    token = create_access_token({"sub": str(citizen.id), "role": "citizen"})
    return TokenOut(access_token=token, role="citizen")


@router.get("/me", response_model=CitizenOut)
def read_me(current_citizen: Citizen = Depends(get_current_citizen)):
    return current_citizen


@router.patch("/me", response_model=CitizenOut)
def update_me(
    payload: CitizenUpdate,
    db: Session = Depends(get_db),
    current_citizen: Citizen = Depends(get_current_citizen),
):
    if payload.email is not None and payload.email != current_citizen.email:
        existing = db.query(Citizen).filter(Citizen.email == payload.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="An account with this email already exists.")
        current_citizen.email = payload.email

    if payload.full_name is not None:
        current_citizen.full_name = payload.full_name
    if payload.phone is not None:
        current_citizen.phone = payload.phone
    if payload.password is not None:
        current_citizen.password_hash = hash_password(payload.password)

    db.add(current_citizen)
    db.commit()
    db.refresh(current_citizen)
    return current_citizen

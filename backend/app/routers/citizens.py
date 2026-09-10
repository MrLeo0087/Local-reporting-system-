from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.citizen import Citizen
from app.schemas.citizen import CitizenRegister, CitizenLogin, CitizenOut, TokenOut
from app.auth.security import hash_password, verify_password, create_access_token
from app.auth.dependencies import get_current_citizen

router = APIRouter(prefix="/citizens", tags=["citizens"])


@router.post("/register", response_model=CitizenOut, status_code=status.HTTP_201_CREATED)
def register(payload: CitizenRegister, db: Session = Depends(get_db)):
    existing = db.query(Citizen).filter(Citizen.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    citizen = Citizen(
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
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

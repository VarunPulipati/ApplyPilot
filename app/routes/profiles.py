"""
Simple CRUD for Profiles so you can store different resume variants.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Profile
from ..schemas import ProfileCreate, ProfileOut

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.post("", response_model=ProfileOut)
def create_profile(payload: ProfileCreate, db: Session = Depends(get_db)):
    obj = Profile(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("", response_model=list[ProfileOut])
def list_profiles(db: Session = Depends(get_db)):
    return db.query(Profile).all()

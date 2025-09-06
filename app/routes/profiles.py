# app/routes/profiles.py
from __future__ import annotations
import secrets, shutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Profile
from pathlib import Path
from ..config import settings

router = APIRouter(prefix="/profiles", tags=["profiles"])
dest_dir = Path(getattr(settings, "resumes_dir", "storage/resumes"))
dest_dir.mkdir(parents=True, exist_ok=True)

# --- Schemas ---
class ProfileCreate(BaseModel):
    name: str
    email: str
    phone: str
    location: str
    skills_csv: str = ""
    resume_path: str = ""  # optional initial value

class ProfilePatch(BaseModel):
    resume_path: Optional[str] = None

# --- CRUD (list/create) ---
@router.get("")
def list_profiles(db: Session = Depends(get_db)):
    return db.query(Profile).all()

@router.post("")
def create_profile(body: ProfileCreate, db: Session = Depends(get_db)):
    prof = Profile(
        name=body.name, email=body.email, phone=body.phone, location=body.location,
        skills_csv=body.skills_csv, resume_path=body.resume_path or ""
    )
    db.add(prof); db.commit(); db.refresh(prof)
    return prof

# --- Upload a resume PDF and bind it to the profile ---
@router.post("/{profile_id}/resume")
async def upload_resume(
    profile_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    prof = db.query(Profile).get(profile_id)
    if not prof:
        raise HTTPException(404, "Profile not found")

    # Ensure destination dir exists
    dest_dir = Path(settings.resumes_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename or "").suffix or ".pdf"
    out_name = f"profile{profile_id}_{secrets.token_hex(6)}{ext}"
    dest = dest_dir / out_name

    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    prof.resume_path = str(dest)
    db.add(prof); db.commit()
    return {"ok": True, "profile_id": profile_id, "resume_path": str(dest)}

# --- Optional: set resume_path directly to an existing file ---
@router.patch("/{profile_id}")
def patch_profile(profile_id: int, body: ProfilePatch, db: Session = Depends(get_db)):
    prof = db.query(Profile).get(profile_id)
    if not prof:
        raise HTTPException(404, "Profile not found")
    if body.resume_path is not None:
        prof.resume_path = body.resume_path
    db.add(prof); db.commit()
    return {"ok": True, "profile_id": prof.id, "resume_path": prof.resume_path}

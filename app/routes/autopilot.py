from __future__ import annotations
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.autopilot import run_batch_apply

router = APIRouter(prefix="/autopilot", tags=["autopilot"])

class BatchRequest(BaseModel):
    profile_id: int = 1
    limit: int = Field(10, ge=1, le=50)
    resume_mode: str = Field("static", pattern="^(ai|static)$")
    submit: bool = True
    delay_seconds: float = Field(3.0, ge=0, le=10)

@router.post("/run")
def run_autopilot(req: BatchRequest, db: Session = Depends(get_db)):
    return run_batch_apply(
        db=db,
        profile_id=req.profile_id,
        limit=req.limit,
        resume_mode=req.resume_mode,
        submit=req.submit,
        delay_seconds=req.delay_seconds,
    )

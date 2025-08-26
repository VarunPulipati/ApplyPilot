"""
Import a job by URL, detect ATS, and persist the record.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Job
from ..services.ats_detect import detect_ats
from ..services.jd_parser import fetch_job_details

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobImportRequest(BaseModel):
    url: str


@router.post("/import")
async def import_job(body: JobImportRequest, db: Session = Depends(get_db)):
    details = await fetch_job_details(body.url)
    ats_type = detect_ats(body.url)

    job = Job(
        url=body.url,
        ats_type=ats_type,
        company=details.get("company", ""),
        title=details.get("title", ""),
        location=details.get("location", ""),
        fields_schema={},
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return {"id": job.id, "ats_type": job.ats_type, "title": job.title}
  
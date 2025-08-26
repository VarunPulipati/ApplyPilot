from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Job
from ..services.sources.greenhouse import fetch_greenhouse_company_jobs
from ..services.sources.lever import fetch_lever_company_jobs

router = APIRouter(prefix="/sources", tags=["sources"])

class ImportRequest(BaseModel):
    source: str               # "greenhouse" | "lever"
    company: str              # boards-id or lever company slug

@router.post("/import-company")
async def import_company_jobs(body: ImportRequest, db: Session = Depends(get_db)):
    if body.source == "greenhouse":
        jobs = await fetch_greenhouse_company_jobs(body.company)
    elif body.source == "lever":
        jobs = await fetch_lever_company_jobs(body.company)
    else:
        raise HTTPException(400, "Unsupported source")

    created = 0
    for j in jobs:
        exists = db.query(Job).filter(Job.url == j["url"]).first()
        if exists: 
            continue
        row = Job(
            url=j["url"], source=j["source"], company=j["company"], title=j["title"],
            location=j["location"], ats_type=j["ats_type"], fields_schema={}
        )
        db.add(row); created += 1
    db.commit()
    return {"imported": created, "total_seen": len(jobs)}

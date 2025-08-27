from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Job
import csv, io
from ..services.ats_detect import detect_ats

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.get("")
def list_jobs(db: Session = Depends(get_db)):
    rows = db.query(Job).order_by(Job.id.desc()).limit(200).all()
    return [{"id":j.id,"title":j.title,"company":j.company,"ats":j.ats_type,"url":j.url} for j in rows]

@router.post("/import-csv")
async def import_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    CSV columns (header row required):
      company,title,url,location,source
    We auto-detect ATS from the URL and store only supported ones.
    """
    raw = (await file.read()).decode("utf-8", errors="ignore")
    rdr = csv.DictReader(io.StringIO(raw))
    created = 0; skipped = 0
    for r in rdr:
        url = (r.get("url") or "").strip()
        if not url: 
            skipped += 1; continue
        if db.query(Job).filter(Job.url == url).first():
            skipped += 1; continue
        ats = detect_ats(url)
        if ats not in {"greenhouse","lever","ashby","workable"}:
            skipped += 1; continue
        job = Job(
            url=url,
            company=r.get("company",""),
            title=r.get("title",""),
            location=r.get("location",""),
            source=r.get("source","csv"),
            ats_type=ats,
            fields_schema={}
        )
        db.add(job); created += 1
    db.commit()
    return {"imported": created, "skipped": skipped}

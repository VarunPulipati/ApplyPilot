from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
from ..database import get_db
from ..models import Job, Application
from ..services.connectors.greenhouse import submit_greenhouse
from ..services.doc_gen import render_resume_html, html_to_pdf
from ..config import settings
from ..services.tracker import log_to_excel
from pathlib import Path
from uuid import uuid4

router = APIRouter(prefix="/apply", tags=["apply"])

class ApplyRequest(BaseModel):
    job_id: int
    profile_name: str = "default"
    qa_pack_id: str = "default"

@router.post("")
def apply_once(body: ApplyRequest, db: Session = Depends(get_db)):
    job = db.query(Job).get(body.job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.ats_type != "greenhouse":
        raise HTTPException(400, "MVP supports greenhouse only")

    # 1) Build a simple resume (stub – plug your profile later)
    ctx = {
        "name":"Your Name","email":"you@example.com","phone":"+1-555-123-4567",
        "location":"NYC, NY","summary":"Pragmatic DS.","skills":["Python","SQL"],
        "experience":[{"role":"Data Analyst","company":job.company or "Company","years":"2024–present","bullets":["Built KPIs","Automated ETL"]}]
    }
    pdf_path = Path(settings.doc_out_dir) / f"resume_{uuid4().hex}.pdf"
    pdf = html_to_pdf(render_resume_html(ctx), str(pdf_path))

    # 2) Minimal answers
    answers = {
        "first_name":"Your","last_name":"Name","email":ctx["email"],"phone":ctx["phone"],
        "work_auth":"Authorized to work in the U.S. (H-1B, valid to Oct 2027).",
        "salary":"Open to discussing; aligned to market range.",
        "why_me":"I ship measurable outcomes; stack: Python, SQL, Spark."
    }

    # 3) Submit
    confirmation = submit_greenhouse(job.url, answers, pdf)

    # 4) Record application
    app_row = Application(job_id=job.id, profile_id=1, qa_pack_id=body.qa_pack_id,
                          status="submitted", confirmation_number=confirmation,
                          submitted_at=datetime.utcnow(), resume_version="v0")
    db.add(app_row); db.commit()

    # 5) Excel
    xlsx = log_to_excel("applications.xlsx", {
        "company": job.company, "role": job.title, "date_applied": datetime.utcnow().isoformat(timespec="seconds"),
        "job_url": job.url, "source": job.source, "ats_type": job.ats_type,
        "confirmation_number": confirmation, "status":"submitted",
        "resume_version":"v0", "notes":""
    })

    return {"ok": True, "confirmation": confirmation, "excel": xlsx}

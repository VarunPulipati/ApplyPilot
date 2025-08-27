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
    simulate: bool = True  # <-- default to safe preview

def readiness_score(job: Job, answers: dict) -> tuple[int, list[str]]:
    issues = []
    score = 0
    if answers.get("first_name") and answers.get("last_name"): score += 20
    else: issues.append("Missing name")
    if answers.get("email"): score += 20
    else: issues.append("Missing email")
    if answers.get("phone"): score += 10
    else: issues.append("Missing phone")
    # Heuristic boosts
    if "work_auth" in answers: score += 20
    if "why_me" in answers and len(answers["why_me"]) > 40: score += 20
    if job.ats_type in {"greenhouse","lever","ashby","workable"}: score += 10
    return min(score, 100), issues

@router.post("")
def apply_once(body: ApplyRequest, db: Session = Depends(get_db)):
    job = db.query(Job).get(body.job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.ats_type not in {"greenhouse"}:   # extend as you add connectors
        raise HTTPException(400, f"MVP supports greenhouse; got {job.ats_type}")

    # --- Build resume (stub; wire Profile later) ---
    ctx = {
        "name":"Your Name","email":"you@example.com","phone":"+1-555-123-4567",
        "location":"NYC, NY","summary":"Pragmatic DS.","skills":["Python","SQL"],
        "experience":[{"role":"Data Analyst","company":job.company or "Company","years":"2024–present","bullets":["Built KPIs","Automated ETL"]}]
    }
    pdf_path = Path(settings.doc_out_dir) / f"resume_{uuid4().hex}.pdf"
    pdf = html_to_pdf(render_resume_html(ctx), str(pdf_path))

    # --- Answers (pull from QABank later) ---
    answers = {
        "first_name":"Your","last_name":"Name","email":ctx["email"],"phone":ctx["phone"],
        "work_auth":"Authorized to work in the U.S. (H-1B, valid to Oct 2027).",
        "salary":"Open to discussing; aligned to market range.",
        "why_me":"I ship measurable outcomes; stack: Python, SQL, Spark."
    }

    # --- Dry-run gate ---
    score, issues = readiness_score(job, answers)
    if body.simulate or score < 70:
        return {
            "simulate": True,
            "score": score,
            "issues": issues,
            "job": {"id": job.id, "title": job.title, "company": job.company, "ats": job.ats_type, "url": job.url},
            "resume_pdf": str(pdf)
        }

    # --- Real submit ---
    confirmation = submit_greenhouse(job.url, answers, pdf)

    app_row = Application(job_id=job.id, profile_id=1, qa_pack_id="default",
                          status="submitted", confirmation_number=confirmation,
                          submitted_at=datetime.utcnow(), resume_version="v0")
    db.add(app_row); db.commit()

    xlsx = log_to_excel("applications.xlsx", {
        "company": job.company, "role": job.title, "date_applied": datetime.utcnow().isoformat(timespec="seconds"),
        "job_url": job.url, "source": job.source, "ats_type": job.ats_type,
        "confirmation_number": confirmation, "status":"submitted",
        "resume_version":"v0", "notes":""
    })

    return {"ok": True, "confirmation": confirmation, "excel": xlsx}

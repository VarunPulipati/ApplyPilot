from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
from pathlib import Path
from uuid import uuid4
import asyncio

from ..database import get_db
from ..models import Job, Application, QABank, Profile
from ..services.doc_gen import render_resume_html, html_to_pdf
from ..services.tailoring import generate_resume_context, draft_answers, standard_answers
from ..services.connectors.greenhouse import collect_questions, submit_greenhouse
from ..services.tracker import log_to_excel
from ..config import settings
from ..services.jd_parser import fetch_job_details

router = APIRouter(prefix="/apply", tags=["apply"])

class ApplyRequest(BaseModel):
    job_id: int
    profile_id: int = 1
    simulate: bool = True         # preview by default
    resume_mode: str = "ai"       # "ai" or "static" (use Profile.resume_path)

@router.post("")
def apply_once(body: ApplyRequest, db: Session = Depends(get_db)):
    job = db.query(Job).get(body.job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.ats_type not in {"greenhouse"}:
        raise HTTPException(400, f"Connector for {job.ats_type} not yet enabled")

    prof = db.query(Profile).get(body.profile_id)
    if not prof:
        raise HTTPException(404, "Profile not found")

    profile = {
        "name": prof.name,
        "email": prof.email,
        "phone": prof.phone,
        "location": prof.location,
        "skills": [s.strip() for s in (prof.skills_csv or "").split(",") if s.strip()]
    }

    # JD text
    jd_details = asyncio.run(fetch_job_details(job.url))
    jd_text = jd_details.get("jd_text","")

    # Experience bank from QABank
    qa_rows = db.query(QABank).all()
    exp_bank = [ {"base_answer": r.base_answer, "tags": r.tags} for r in qa_rows ]

    # Resume (AI or static)
    if body.resume_mode == "static" and prof.resume_path:
        resume_pdf_path = prof.resume_path
    else:
        resume_ctx = generate_resume_context(profile, jd_text, exp_bank)
        resume_pdf_path = str(Path(settings.doc_out_dir) / f"resume_{uuid4().hex}.pdf")
        html = render_resume_html(resume_ctx)
        html_to_pdf(html, resume_pdf_path)

    # Collect form questions and draft answers via AI
    questions = collect_questions(job.url)
    custom_answers = draft_answers(questions, profile, exp_bank, jd_text)

    # Structured fields
    std = standard_answers(profile)

    if body.simulate:
        return {
            "simulate": True,
            "job": {"id": job.id, "title": job.title, "company": job.company, "url": job.url, "ats": job.ats_type},
            "resume_pdf": resume_pdf_path,
            "found_questions": questions,
            "draft_answers": custom_answers
        }

    # Submit
    confirmation = submit_greenhouse(job.url, std, resume_pdf_path, custom_answers)

    app_row = Application(
        job_id=job.id, profile_id=prof.id, qa_pack_id="default",
        status="submitted", confirmation_number=confirmation,
        submitted_at=datetime.utcnow(), resume_version=("static" if body.resume_mode=="static" else "ai-v1"),
    )
    db.add(app_row); db.commit()

    xlsx = log_to_excel("applications.xlsx", {
        "company": job.company, "role": job.title, "date_applied": datetime.utcnow().isoformat(timespec="seconds"),
        "job_url": job.url, "source": job.source, "ats_type": job.ats_type,
        "confirmation_number": confirmation, "status":"submitted",
        "resume_version": ("static" if body.resume_mode=="static" else "ai-v1"), "notes":""
    })
    return {"ok": True, "confirmation": confirmation, "excel": xlsx}

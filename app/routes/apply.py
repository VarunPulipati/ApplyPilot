# app/routes/apply.py
from __future__ import annotations

import asyncio
import traceback
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Application, Job, Profile, QABank
from ..services.doc_gen import render_resume_html, html_to_pdf
from ..services.jd_parser import fetch_job_details
from ..services.tailoring import (
    generate_resume_context,
    draft_answers,
    standard_answers,
)
from ..services.connectors.greenhouse import (
    collect_questions,
    submit_greenhouse,
)
from ..services.tracker import log_to_excel

router = APIRouter(prefix="/apply", tags=["apply"])


class ApplyRequest(BaseModel):
    """
    Request body for /apply
    - job_id: which job to apply to
    - profile_id: which saved profile to use for contact/skills
    - simulate: when True, build resume + draft answers but DO NOT submit
    - resume_mode: "ai" (generate tailored resume) or "static" (use Profile.resume_path)
    """
    job_id: int
    profile_id: int = 1
    simulate: bool = True
    resume_mode: str = "ai"  # "ai" or "static"


@router.post("")
def apply_once(body: ApplyRequest, db: Session = Depends(get_db)):
    """
    Preview then submit an application to a supported ATS (MVP: Greenhouse).
    - In simulate mode, returns: resume_pdf path, scraped questions, ai-drafted answers.
    - On real submit, also writes Application row + logs to applications.xlsx.
    """
    try:
        # --- 0) Load job & profile ---
        job: Job | None = db.query(Job).get(body.job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.ats_type not in {"greenhouse"}:
            raise HTTPException(
                status_code=400, detail=f"Connector for {job.ats_type} not yet enabled"
            )

        prof: Profile | None = db.query(Profile).get(body.profile_id)
        if not prof:
            raise HTTPException(status_code=404, detail="Profile not found")

        profile = {
            "name": prof.name,
            "email": prof.email,
            "phone": prof.phone,
            "location": prof.location,
            "skills": [
                s.strip()
                for s in (prof.skills_csv or "").split(",")
                if s.strip()
            ],
        }

        # Ensure output directory exists for generated PDFs
        Path(settings.doc_out_dir).mkdir(parents=True, exist_ok=True)

        # --- 1) Fetch JD text (async helper run from sync route) ---
        jd_details = asyncio.run(fetch_job_details(job.url))
        jd_text = jd_details.get("jd_text", "")

        # --- 2) Experience bank from QABank (your truth source) ---
        qa_rows = db.query(QABank).all()
        exp_bank = [{"base_answer": r.base_answer, "tags": r.tags} for r in qa_rows]

        # --- 3) Resume (AI-tailored or static master) ---
        if body.resume_mode == "static" and prof.resume_path:
            resume_pdf_path = prof.resume_path
        else:
            resume_ctx = generate_resume_context(profile, jd_text, exp_bank)
            resume_pdf_path = str(
                Path(settings.doc_out_dir) / f"resume_{uuid4().hex}.pdf"
            )
            html = render_resume_html(resume_ctx)
            # convert HTML -> PDF (Playwright)
            html_to_pdf(html, resume_pdf_path)

        # --- 4) Scrape application questions + draft AI answers ---
        # (connector normalizes Datadog-style wrapper links to real Greenhouse)
        questions = collect_questions(job.url, job.company or "")
        custom_answers = draft_answers(questions, profile, exp_bank, jd_text)

        # --- 5) Structured fields (name/email/phone) ---
        std = standard_answers(profile)

        # --- 6) Preview only ---
        if body.simulate:
            return {
                "simulate": True,
                "job": {
                    "id": job.id,
                    "title": job.title,
                    "company": job.company,
                    "url": job.url,
                    "ats": job.ats_type,
                },
                "resume_pdf": resume_pdf_path,
                "found_questions": questions,
                "draft_answers": custom_answers,
            }

        # --- 7) Real submit (opens browser, uploads, fills, submits) ---
        confirmation = submit_greenhouse(
            job.url,
            std,
            resume_pdf_path,
            custom_answers,
            job.company or "",
        )

        # --- 8) Persist Application row ---
        app_row = Application(
            job_id=job.id,
            profile_id=prof.id,
            qa_pack_id="default",
            status="submitted",
            confirmation_number=confirmation,
            submitted_at=datetime.utcnow(),
            resume_version=("static" if body.resume_mode == "static" else "ai-v1"),
        )
        db.add(app_row)
        db.commit()

        # --- 9) Log to Excel tracker ---
        xlsx = log_to_excel(
            "applications.xlsx",
            {
                "company": job.company,
                "role": job.title,
                "date_applied": datetime.utcnow().isoformat(timespec="seconds"),
                "job_url": job.url,
                "source": job.source,
                "ats_type": job.ats_type,
                "confirmation_number": confirmation,
                "status": "submitted",
                "resume_version": (
                    "static" if body.resume_mode == "static" else "ai-v1"
                ),
                "notes": "",
            },
        )

        return {"ok": True, "confirmation": confirmation, "excel": xlsx}

    except HTTPException:
        # re-raise FastAPI errors as-is
        raise
    except Exception as e:
        # print full trace to server console and expose a readable error in the response
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"apply_failed: {type(e).__name__}: {e}"
        )

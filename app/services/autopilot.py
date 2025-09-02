# app/services/autopilot.py
from __future__ import annotations

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from ..config import settings
from ..models import Application, Job, Profile, QABank
from .doc_gen import html_to_pdf, render_resume_html
from .jd_parser import fetch_job_details
from .tailoring import draft_answers, generate_resume_context, standard_answers
from .connectors.greenhouse import collect_questions, submit_greenhouse
from .tracker import log_leads_to_excel, log_to_excel


# ---------- helpers ----------

def _pick_jobs(db: Session, limit: int, only_unapplied: bool = True) -> List[Job]:
    """Pick latest jobs, optionally excluding ones already in Applications."""
    q = db.query(Job)
    if only_unapplied:
        q = q.outerjoin(Application, Application.job_id == Job.id).filter(
            Application.id.is_(None)
        )
    return q.order_by(Job.id.desc()).limit(limit).all()


def _profile_dict(prof: Profile) -> Dict[str, Any]:
    return {
        "name": prof.name,
        "email": prof.email,
        "phone": prof.phone,
        "location": prof.location,
        "skills": [
            s.strip() for s in (prof.skills_csv or "").split(",") if s.strip()
        ],
    }


def _make_resume(
    profile: Dict[str, Any],
    jd_text: str,
    exp_bank: List[Dict[str, str]],
    resume_mode: str,
    static_path: Optional[str],
) -> str:
    """Return a PDF path (uses static path or generates AI resume)."""
    if resume_mode == "static" and static_path:
        return static_path
    ctx = generate_resume_context(profile, jd_text, exp_bank)
    out = Path(settings.doc_out_dir) / f"resume_{uuid4().hex}.pdf"
    html = render_resume_html(ctx)
    html_to_pdf(html, str(out))
    return str(out)


def _run_async_safely(coro):
    """Run an async coroutine from sync code; handle already-running loop."""
    try:
        return asyncio.run(coro)
    except RuntimeError:
        # If an event loop is already running (rare in this sync context)
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)


# ---------- batch engine ----------

def run_batch_apply(
    db: Session,
    profile_id: int,
    limit: int = 10,
    resume_mode: str = "static",  # "static" or "ai"
    submit: bool = True,
    delay_seconds: float = 3.0,
) -> Dict[str, Any]:
    """
    Pick N unapplied jobs and (preview -> optionally submit) each.
    Returns a summary with successes/failures and Excel paths.
    """
    prof = db.query(Profile).get(profile_id)
    if not prof:
        return {"ok": False, "error": "Profile not found"}

    profile = _profile_dict(prof)

    # Experience/QABank
    qa_rows = db.query(QABank).all()
    exp_bank = [{"base_answer": r.base_answer, "tags": r.tags} for r in qa_rows]

    # Choose jobs
    jobs = _pick_jobs(db, limit=limit, only_unapplied=True)
    if not jobs:
        return {
            "ok": True,
            "picked": 0,
            "results": [],
            "note": "No unapplied jobs available",
        }

    # Save “picked” list to leads.xlsx
    leads_rows = [
        {"company": j.company, "title": j.title, "job_url": j.url, "ats_type": j.ats_type}
        for j in jobs
    ]
    leads_xlsx = log_leads_to_excel("leads.xlsx", leads_rows)

    results: List[Dict[str, Any]] = []
    for j in jobs:
        entry: Dict[str, Any] = {
            "job_id": j.id,
            "company": j.company,
            "title": j.title,
            "url": j.url,
        }
        try:
            # JD → text
            try:
                jd_details = _run_async_safely(fetch_job_details(j.url))
            except Exception:
                jd_details = {}
            jd_text = (jd_details or {}).get("jd_text", "")

            # Resume
            resume_pdf = _make_resume(
                profile, jd_text, exp_bank, resume_mode, prof.resume_path
            )
            entry["resume_pdf"] = resume_pdf

            # Questions + AI answers
            if j.ats_type == "greenhouse":
                questions = collect_questions(j.url, j.company or "")
            else:
                questions = []
            answers = draft_answers(questions, profile, exp_bank, jd_text)
            entry["found_questions"] = questions
            entry["draft_answers"] = answers

            # Structured fields
            std = standard_answers(profile)

            if submit:
                if j.ats_type != "greenhouse":
                    raise RuntimeError(f"ATS {j.ats_type} not supported yet")

                confirmation = submit_greenhouse(
                    j.url, std, resume_pdf, answers, j.company or ""
                )
                entry["confirmation"] = confirmation or ""

                # Persist application row
                app_row = Application(
                    job_id=j.id,
                    profile_id=prof.id,
                    qa_pack_id="default",
                    status="submitted",
                    confirmation_number=confirmation,
                    submitted_at=datetime.utcnow(),
                    resume_version=("static" if resume_mode == "static" else "ai-v1"),
                )
                db.add(app_row)
                db.commit()

                # Excel tracker
                xlsx = log_to_excel(
                    "applications.xlsx",
                    {
                        "company": j.company,
                        "role": j.title,
                        "date_applied": datetime.utcnow().isoformat(timespec="seconds"),
                        "job_url": j.url,
                        "source": j.source,
                        "ats_type": j.ats_type,
                        "confirmation_number": confirmation,
                        "status": "submitted",
                        "resume_version": (
                            "static" if resume_mode == "static" else "ai-v1"
                        ),
                        "notes": "",
                    },
                )
                entry["status"] = "submitted"
                entry["applications_xlsx"] = xlsx
            else:
                entry["status"] = "previewed"

            results.append(entry)
            time.sleep(delay_seconds)

        except Exception as e:
            entry["status"] = "failed"
            entry["error"] = f"{type(e).__name__}: {e}"
            results.append(entry)
            time.sleep(1.0)

    ok = any(r.get("status") in {"previewed", "submitted"} for r in results)
    return {
        "ok": ok,
        "picked": len(jobs),
        "submit": submit,
        "leads_xlsx": leads_xlsx,
        "results": results,
    }

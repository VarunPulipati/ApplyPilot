"""
Endpoints to generate application “packages” (resume/cover PDFs).
For MVP, we demo just the resume generation.
"""

from uuid import uuid4
from pathlib import Path
from fastapi import APIRouter
from ..services.doc_gen import render_resume_html, html_to_pdf
from ..config import settings

router = APIRouter(prefix="/packages", tags=["packages"])


@router.post("/generate-resume")
def generate_resume_demo():
    """
    Demo-only endpoint: fills a static context to produce a PDF resume.
    Replace with dynamic data from Profile + tailoring later.
    """
    context = {
        "name": "Your Name",
        "email": "you@example.com",
        "phone": "+1-555-123-4567",
        "location": "NYC, NY",
        "summary": "Data scientist who ships pragmatic, measurable ML.",
        "skills": ["Python", "SQL", "PySpark", "Databricks", "Power BI"],
        "experience": [
            {
                "role": "Data Analyst",
                "company": "RaceTrac",
                "years": "2024–present",
                "bullets": ["Built KPIs for loyalty", "Automated ETL in Databricks"],
            }
        ],
    }
    html = render_resume_html(context)
    out_path = Path(settings.doc_out_dir) / f"resume_{uuid4().hex}.pdf"
    pdf_path = html_to_pdf(html, str(out_path))
    return {"ok": True, "pdf_path": pdf_path}

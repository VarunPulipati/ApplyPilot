"""
Generate PDFs without LibreOffice:
- Render HTML with Jinja2 templates
- Print to PDF via Playwright (Chromium)
"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright
from ..config import settings

# Prepare a Jinja2 environment pointing at /templates
env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "xml"])
)


def render_resume_html(context: dict) -> str:
    """
    Render the resume HTML from templates/resume.html.j2
    context: dict containing name, email, phone, summary, skills, experience, etc.
    """
    tpl = env.get_template("resume.html.j2")
    return tpl.render(**context)


def html_to_pdf(html: str, out_path: str) -> str:
    """
    Use Playwright to render HTML and export it as a PDF.
    """
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()  # headless by default
        page = browser.new_page()
        page.set_content(html, wait_until="load")   # load CSS/fonts before printing
        page.emulate_media(media="print")           # ensures print CSS rules apply
        page.pdf(
            path=str(out),
            format="Letter",
            print_background=True,
            margin={"top": "0.5in", "bottom": "0.5in", "left": "0.5in", "right": "0.5in"},
        )
        browser.close()

    return str(out)

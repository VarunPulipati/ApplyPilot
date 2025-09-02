# app/services/doc_gen.py
from __future__ import annotations

import os
import asyncio
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright

from ..config import settings

def _env() -> Environment:
    tmpl_dir: Path = settings.template_path
    if not tmpl_dir.exists():
        raise FileNotFoundError(f"Template directory not found: {tmpl_dir}")
    return Environment(
        loader=FileSystemLoader(str(tmpl_dir)),
        autoescape=select_autoescape(["html", "j2", "jinja"]),
    )

def render_resume_html(ctx: dict) -> str:
    tpl = _env().get_template("resume.html.j2")  # make sure this file exists
    return tpl.render(**ctx)

def html_to_pdf(html: str, out_path: str) -> str:
    # Windows event loop policy (Playwright needs Proactor)
    if os.name == "nt":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except Exception:
            pass

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html, wait_until="load")
        page.emulate_media(media="screen")
        page.pdf(path=str(out), print_background=True, prefer_css_page_size=True)
        browser.close()

    return str(out)

# app/services/doc_gen.py
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateNotFound

from .winloop import run_playwright           # Windows-safe wrapper
from ..config import settings


# --------------------------
# Templates
# --------------------------
def _resolve_templates_dir() -> Path:
    """
    Resolve the templates directory:
    - Prefer settings.template_path if present,
    - else settings.template_dir,
    - else ./templates.
    """
    raw = getattr(settings, "template_path", None)
    if raw:
        base = Path(raw)
    else:
        base = Path(getattr(settings, "template_dir", "templates"))

    if not base.is_absolute():
        base = (Path(__file__).resolve().parents[2] / base).resolve()

    base.mkdir(parents=True, exist_ok=True)
    return base


_DEFAULT_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>{{ profile.name or "Candidate" }} — Resume</title>
  <style>
    html, body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, "Helvetica Neue", Helvetica, sans-serif; color:#111; }
    .wrap { max-width: 800px; margin: 32px auto; }
    h1 { font-size: 28px; margin: 0 0 4px; }
    .sub { color:#555; margin: 0 0 12px; font-size: 14px; }
    h2 { font-size: 18px; margin: 24px 0 8px; border-bottom: 1px solid #ddd; padding-bottom: 4px; }
    ul { margin: 8px 0 0 20px; }
    li { margin: 6px 0; }
    .skills span { display:inline-block; border:1px solid #ccc; border-radius: 10px; padding:2px 8px; margin:4px 6px 0 0; font-size: 12px;}
    .section { page-break-inside: avoid; }
  </style>
</head>
<body>
<div class="wrap">
  <h1>{{ profile.name }}</h1>
  <p class="sub">
    {{ profile.location }} · {{ profile.email }} · {{ profile.phone }}
  </p>

  <div class="section">
    <h2>Professional Summary</h2>
    <p>{{ summary or "Data/ML professional with hands-on experience across Python, SQL, Spark, Databricks, and cloud analytics. Passionate about building reliable data products and measurable business impact." }}</p>
  </div>

  {% if highlights %}
  <div class="section">
    <h2>Highlights</h2>
    <ul>
      {% for h in highlights %}
      <li>{{ h }}</li>
      {% endfor %}
    </ul>
  </div>
  {% endif %}

  {% if experiences %}
  <div class="section">
    <h2>Experience</h2>
    <ul>
      {% for item in experiences %}
      <li>
        <strong>{{ item.title }}</strong> — {{ item.company }}{% if item.when %} ({{ item.when }}){% endif %}
        <ul>
          {% for b in item.bullets %}<li>{{ b }}</li>{% endfor %}
        </ul>
      </li>
      {% endfor %}
    </ul>
  </div>
  {% endif %}

  {% if profile.skills %}
  <div class="section">
    <h2>Skills</h2>
    <div class="skills">
      {% for s in profile.skills %}<span>{{ s }}</span>{% endfor %}
    </div>
  </div>
  {% endif %}
</div>
</body>
</html>
"""


def _ensure_default_template(tmpl_dir: Path) -> None:
    """Create templates/resume.html.j2 if missing."""
    tpl = tmpl_dir / "resume.html.j2"
    if not tpl.exists():
        tpl.write_text(_DEFAULT_TEMPLATE, encoding="utf-8")


def _env() -> Environment:
    tmpl_dir = _resolve_templates_dir()
    _ensure_default_template(tmpl_dir)
    return Environment(
        loader=FileSystemLoader(str(tmpl_dir)),
        autoescape=select_autoescape(["html", "j2", "jinja"]),
        enable_async=False,
    )


# --------------------------
# Public API
# --------------------------
def render_resume_html(ctx: Dict[str, Any]) -> str:
    """Render resume HTML from templates/resume.html.j2 with context."""
    env = _env()
    try:
        tpl = env.get_template("resume.html.j2")
    except TemplateNotFound:
        _ensure_default_template(_resolve_templates_dir())
        tpl = env.get_template("resume.html.j2")
    return tpl.render(**ctx)


def _pdf_from_html_with_playwright(html: str, out_path: Path) -> None:
    """Generate a PDF via Playwright; run through winloop to be Windows-safe."""
    def _impl():
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content(html, wait_until="load")
            page.emulate_media(media="screen")
            page.pdf(
                path=str(out_path),
                print_background=True,
                prefer_css_page_size=True,
            )
            browser.close()
    run_playwright(_impl)


def html_to_pdf(html: str, out_path: str) -> str:
    """Convert HTML to a PDF at out_path and return the absolute path."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    _pdf_from_html_with_playwright(html, out)
    return str(out)

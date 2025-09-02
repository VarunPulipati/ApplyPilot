from __future__ import annotations
from typing import List, Dict, Optional
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright

def _extract_job_id(url: str) -> Optional[str]:
    u = urlparse(url)
    q = parse_qs(u.query or "")
    if "gh_jid" in q and q["gh_jid"]:
        return q["gh_jid"][0]
    # fallback: /detail/<jid>/ style
    parts = [p for p in u.path.split("/") if p]
    for i, p in enumerate(parts):
        if p.isdigit():
            return p
    return None

def _to_embed_url(url: str, company_slug: Optional[str]) -> Optional[str]:
    """
    Build the Greenhouse embed URL directly, e.g.:
    https://boards.greenhouse.io/embed/job_app?for=datadog&token=7171039
    """
    jid = _extract_job_id(url)
    if not jid or not company_slug:
        return None
    return f"https://boards.greenhouse.io/embed/job_app?for={company_slug}&token={jid}"

def _goto_greenhouse_form(page, url: str, company_slug: Optional[str]) -> None:
    """
    Prefer going straight to the Greenhouse embed form to avoid wrappers/iframes.
    Fallbacks: wrapper -> iframe src -> greenhouse link -> stay on wrapper.
    """
    embed = _to_embed_url(url, company_slug)
    if embed:
        page.goto(embed, wait_until="domcontentloaded")
        return

    page.goto(url, wait_until="domcontentloaded")

    # Already on greenhouse?
    if ("greenhouse.io" in page.url) or ("boards.greenhouse.io" in page.url):
        return

    # Try iframe -> greenhouse
    iframe = page.locator('iframe[src*="greenhouse.io"]').first
    if iframe.count():
        src = iframe.get_attribute("src")
        if src:
            page.goto(src, wait_until="domcontentloaded")
            return

    # Try anchor -> greenhouse
    link = page.locator('a[href*="greenhouse.io"], a[href*="boards.greenhouse.io"]').first
    if link.count():
        href = link.get_attribute("href")
        if href:
            page.goto(href, wait_until="domcontentloaded")
            return
    # else: stay on wrapper; some forms render via JS later

def _collect_labels(page) -> List[str]:
    texts: List[str] = []
    for sel in [
        "label",
        ".field label",
        ".application-label",
        ".application__label",
        ".css-1w8x5l4 label",  # some themes
    ]:
        for el in page.locator(sel).all():
            t = (el.text_content() or "").strip()
            if t and len(t) > 3 and t not in texts:
                texts.append(t)
    return texts

def collect_questions(app_url: str, company_slug: Optional[str] = None) -> List[str]:
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page()
        _goto_greenhouse_form(pg, app_url, company_slug)
        pg.wait_for_load_state("networkidle")
        try:
            pg.wait_for_selector("textarea, input, label", timeout=5000)
        except Exception:
            pass

        qs: List[str] = []

        # Labels (free text, selects, etc.)
        qs.extend(_collect_labels(pg))

        # Placeholders for TEXT inputs that often act as short-answer prompts
        # (skip the basics we fill separately)
        skip_keys = ["first name", "last name", "email", "phone", "resume", "cv"]
        for inp in pg.locator('input[type="text"], input[type="url"], input[type="search"]').all():
            ph = (inp.get_attribute("placeholder") or "").strip()
            if ph and ph.lower() not in skip_keys and ph not in qs:
                qs.append(ph)

        # Textarea placeholders (long-form)
        for ta in pg.locator("textarea").all():
            ph = (ta.get_attribute("placeholder") or "").strip()
            if ph and ph not in qs:
                qs.append(ph)

        b.close()
        return qs

def submit_greenhouse(app_url: str, std: Dict[str, str], resume_pdf: str,
                      custom_answers: Dict[str, str], company_slug: Optional[str] = None) -> str:
    with sync_playwright() as p:
        b = p.chromium.launch(headless=False)
        pg = b.new_page()
        _goto_greenhouse_form(pg, app_url, company_slug)
        pg.wait_for_load_state("domcontentloaded")

        # Upload resume if present
        if pg.locator('input[type="file"]').count():
            pg.set_input_files('input[type="file"]', resume_pdf)

        def fill(sel, val):
            if val and pg.locator(sel).count():
                pg.fill(sel, val)

        # basic fields
        fill('input[name*="first_name" i]', std.get("first_name"))
        fill('input[name*="last_name" i]',  std.get("last_name"))
        fill('input[type="email"]',          std.get("email"))
        fill('input[type="tel"]',            std.get("phone"))

        labels = _collect_labels(pg)

        # Fill textareas (map by label order or placeholder)
        tas = pg.locator("textarea").all()
        for i, ta in enumerate(tas):
            key = labels[i] if i < len(labels) else (ta.get_attribute("placeholder") or "")
            key = (key or "").strip()
            val = custom_answers.get(key) or next(iter(custom_answers.values()), "")
            if val:
                ta.fill(val)

        # Try to fill common short inputs if we have matching answers
        for inp in pg.locator('input[type="text"], input[type="url"]').all():
            key = (inp.get_attribute("placeholder") or "").strip()
            val = custom_answers.get(key)
            if val:
                inp.fill(val)

        # Submit
        for sel in ['button:has-text("Submit")', 'button:has-text("Apply")',
                    'button[type="submit"]', 'input[type="submit"]']:
            if pg.locator(sel).count():
                pg.click(sel)
                break

        pg.wait_for_load_state("networkidle")
        conf = pg.locator('text=/thank you|application submitted|confirmation/i').first
        txt = (conf.text_content() or "").strip() if conf and conf.is_visible() else ""
        b.close()
        return txt

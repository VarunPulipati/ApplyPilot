# app/services/connectors/greenhouse.py
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs

# Type-only import is fine (lightweight); we import sync_playwright inside functions
from playwright.sync_api import Page

from ..winloop import run_playwright
from config import settings


# ---------- URL helpers ----------
def _extract_job_id(url: str) -> Optional[str]:
    u = urlparse(url)
    q = parse_qs(u.query or "")
    if "gh_jid" in q and q["gh_jid"]:
        return q["gh_jid"][0]
    # also support /detail/<jid>/ pattern
    for part in [p for p in u.path.split("/") if p]:
        if part.isdigit():
            return part
    return None


def _to_embed_url(url: str, company_slug: Optional[str]) -> Optional[str]:
    jid = _extract_job_id(url)
    if not jid or not company_slug:
        return None
    return f"https://boards.greenhouse.io/embed/job_app?for={company_slug}&token={jid}"


def _goto_greenhouse_form(page: Page, url: str, company_slug: Optional[str]) -> None:
    """Prefer embed URL. Else land on wrapper → iframe → direct link."""
    embed = _to_embed_url(url, company_slug)
    if embed:
        page.goto(embed, wait_until="domcontentloaded")
        return

    page.goto(url, wait_until="domcontentloaded")

    # already on greenhouse?
    if ("greenhouse.io" in page.url) or ("boards.greenhouse.io" in page.url):
        return

    # wrapper page with GH iframe?
    iframe = page.locator('iframe[src*="greenhouse.io"]').first
    if iframe.count():
        src = iframe.get_attribute("src")
        if src:
            page.goto(src, wait_until="domcontentloaded")
            return

    # wrapper with link to GH?
    link = page.locator('a[href*="greenhouse.io"], a[href*="boards.greenhouse.io"]').first
    if link.count():
        href = link.get_attribute("href")
        if href:
            page.goto(href, wait_until="domcontentloaded")
            return


# ---------- field utilities ----------
_BASIC_KEYS = {"first name", "last name", "email", "phone", "resume", "cv"}


def _label_for_textarea(page: Page, ta_locator) -> str:
    """Best-effort label for a <textarea>."""
    try:
        txt = ta_locator.get_attribute("aria-label") or ta_locator.get_attribute("placeholder")
        if txt:
            return txt.strip()
    except Exception:
        pass

    # try various DOM relationships for a nearby label
    try:
        lab = ta_locator.evaluate(
            """
            (el) => {
              const id = el.getAttribute('id');
              if (id) {
                const byFor = document.querySelector(`label[for="${id}"]`);
                if (byFor) return byFor.innerText;
              }
              const wrap = el.closest('label');
              if (wrap) return wrap.innerText;

              let prev = el.previousElementSibling;
              while (prev) {
                if (prev.tagName && prev.tagName.toLowerCase() === 'label') return prev.innerText;
                prev = prev.previousElementSibling;
              }
              const c = el.closest('div,section,li,fieldset');
              if (c) {
                const any = c.querySelector('label');
                if (any) return any.innerText;
              }
              return "";
            }
            """
        )
        return (lab or "").strip()
    except Exception:
        return ""


def _visible_textarea_keys(page: Page) -> List[str]:
    """Return keys for each visible <textarea> in order."""
    out: List[str] = []
    tas = page.locator("textarea:visible")
    for i in range(tas.count()):
        ta = tas.nth(i)
        key = (ta.get_attribute("aria-label") or ta.get_attribute("placeholder") or "").strip()
        if not key:
            key = _label_for_textarea(page, ta)
        if not key:
            key = f"question_{i+1}"
        out.append(key)
    return out


def _fill_contenteditable(page: Page, sel: str, text: str) -> bool:
    """Best-effort fill for rich-text editors."""
    loc = page.locator(f"{sel}:visible")
    if not loc.count():
        return False
    try:
        el = loc.first
        el.click()
        page.keyboard.press("Control+A")
        page.keyboard.press("Delete")
        page.keyboard.type(text)
        return True
    except Exception:
        return False


# ---------- public API ----------
def collect_questions(app_url: str, company_slug: Optional[str] = None) -> List[str]:
    """
    Return ONLY long-answer prompts (for visible <textarea> elements).
    """
    def _impl():
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            pg = b.new_page()
            _goto_greenhouse_form(pg, app_url, company_slug)
            pg.wait_for_load_state("networkidle")
            try:
                pg.wait_for_selector("textarea, input, label", timeout=5000)
            except Exception:
                pass
            keys = _visible_textarea_keys(pg)
            b.close()
            return keys

    return run_playwright(_impl)


def submit_greenhouse(
    app_url: str,
    std: Dict[str, str],
    resume_pdf: str,
    custom_answers: Dict[str, str],
    company_slug: Optional[str] = None,
    debug: bool = False,
) -> Tuple[str, Dict]:
    """
    Upload resume, fill standard fields, answer long-form questions, submit.
    Returns (confirmation_text, debug_info).
    """
    def _impl():
        from playwright.sync_api import sync_playwright
        headless = bool(getattr(settings, "playwright_headless", True))

        debug_dir = Path(getattr(settings, "doc_out_dir", "storage/docs")) / "debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        shots: Dict[str, str] = {}
        filled: List[Dict] = []

        with sync_playwright() as p:
            b = p.chromium.launch(headless=headless)
            pg = b.new_page()
            _goto_greenhouse_form(pg, app_url, company_slug)
            pg.wait_for_load_state("domcontentloaded")

            # upload resume if input present
            if pg.locator('input[type="file"]').count():
                try:
                    pg.set_input_files('input[type="file"]', resume_pdf)
                except Exception:
                    pass

            # basic fields helper
            def fill(sel: str, val: Optional[str]):
                if not val:
                    return
                loc = pg.locator(sel)
                if loc.count():
                    try:
                        loc.first.fill(val)
                    except Exception:
                        try:
                            loc.first.click()
                            pg.keyboard.type(val)
                        except Exception:
                            pass

            fill('input[name*="first_name" i]', std.get("first_name"))
            fill('input[name*="last_name"  i]', std.get("last_name"))
            fill('input[type="email"]',          std.get("email"))
            fill('input[type="tel"]',            std.get("phone"))

            # long-answer textareas
            keys = _visible_textarea_keys(pg)
            tas  = pg.locator("textarea:visible")
            for i in range(tas.count()):
                ta  = tas.nth(i)
                key = keys[i] if i < len(keys) else f"question_{i+1}"
                val = (custom_answers.get(key) or custom_answers.get(key.lower()) or "").strip()
                if not val:
                    # keep test forms non-empty so you can see it working
                    val = f"{std.get('first_name','I')} have relevant experience for \"{key}\". Happy to discuss in detail."
                try:
                    ta.fill(val)
                    filled.append({"key": key, "chars": len(val)})
                except Exception:
                    try:
                        ta.click()
                        pg.keyboard.type(val)
                        filled.append({"key": key, "chars": len(val), "typed": True})
                    except Exception:
                        filled.append({"key": key, "error": "could_not_fill"})

            if debug:
                before = debug_dir / "before_submit.png"
                try:
                    pg.screenshot(path=str(before), full_page=True)
                    shots["before"] = str(before)
                except Exception:
                    pass

            # submit
            submitted = False
            for sel in ['button:has-text("Submit")', 'button:has-text("Apply")',
                        'button[type="submit"]', 'input[type="submit"]']:
                if pg.locator(sel).count():
                    try:
                        pg.click(sel)
                        submitted = True
                    except Exception:
                        pass
                    break

            if submitted:
                try:
                    pg.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass

            if debug:
                after = debug_dir / "after_submit.png"
                try:
                    pg.screenshot(path=str(after), full_page=True)
                    shots["after"] = str(after)
                except Exception:
                    pass

            # best-effort confirmation
            conf_txt = ""
            try:
                el = pg.locator('text=/thank you|application submitted|confirmation/i').first
                if el and el.is_visible():
                    conf_txt = (el.text_content() or "").strip()
            except Exception:
                pass

            b.close()
            return conf_txt, {"filled": filled, "shots": shots}

    return run_playwright(_impl)

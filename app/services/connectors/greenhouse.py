from __future__ import annotations
from typing import List, Dict
from playwright.sync_api import sync_playwright

def collect_questions(app_url: str) -> List[str]:
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page()
        pg.goto(app_url, wait_until="domcontentloaded")
        qs: List[str] = []
        for sel in ["label", ".field label", ".application-label"]:
            for el in pg.locator(sel).all():
                t = (el.text_content() or "").strip()
                if t and len(t) > 3 and t not in qs:
                    qs.append(t)
        for t in pg.locator("textarea").all():
            ph = (t.get_attribute("placeholder") or "").strip()
            if ph and ph not in qs:
                qs.append(ph)
        b.close()
        return qs

def submit_greenhouse(app_url: str, std: Dict[str,str], resume_pdf: str, custom_answers: Dict[str,str]) -> str:
    with sync_playwright() as p:
        b = p.chromium.launch(headless=False)
        pg = b.new_page()
        pg.goto(app_url, wait_until="domcontentloaded")

        # Upload resume
        if pg.locator('input[type="file"]').count():
            pg.set_input_files('input[type="file"]', resume_pdf)

        def fill(sel, val):
            if val and pg.locator(sel).count():
                pg.fill(sel, val)

        # basics
        fill('input[name*="first_name" i]', std.get("first_name"))
        fill('input[name*="last_name" i]',  std.get("last_name"))
        fill('input[type="email"]',          std.get("email"))
        fill('input[type="tel"]',            std.get("phone"))

        # textareas: map in label order; fallback to first answer
        labels = []
        for el in pg.locator("label").all():
            t = (el.text_content() or "").strip()
            if t: labels.append(t)
        tas = pg.locator("textarea").all()
        for i, t in enumerate(tas):
            key = labels[i] if i < len(labels) else ""
            val = custom_answers.get(key) or next(iter(custom_answers.values()), "")
            if val: t.fill(val)

        # submit
        for sel in ['button:has-text("Submit")','button:has-text("Apply")','button[type="submit"]','input[type="submit"]']:
            if pg.locator(sel).count():
                pg.click(sel); break
        pg.wait_for_load_state("networkidle")
        conf = pg.locator('text=/thank you|application submitted|confirmation/i').first
        txt = (conf.text_content() or "").strip() if conf and conf.is_visible() else ""
        b.close()
        return txt

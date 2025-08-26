# app/services/connectors/greenhouse.py
from playwright.sync_api import sync_playwright

def submit_greenhouse(app_url: str, answers: dict, resume_pdf: str) -> str:
    """
    Opens a Greenhouse application URL, uploads resume, fills common fields,
    answers visible textareas, clicks submit, and returns a confirmation snippet.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # show window in case of CAPTCHA
        page = browser.new_page()
        page.goto(app_url, wait_until="domcontentloaded")

        # Upload resume if there is a file field
        file_inputs = page.locator('input[type="file"]')
        if file_inputs.count() > 0:
            file_inputs.first.set_input_files(resume_pdf)

        # Helper to fill if field exists
        def maybe_fill(selector: str, value: str | None):
            if not value:
                return
            loc = page.locator(selector)
            if loc.count() > 0:
                loc.first.fill(value)

        # Basic fields (best-effort)
        maybe_fill('input[name*="first_name" i]', answers.get("first_name"))
        maybe_fill('input[name*="last_name" i]',  answers.get("last_name"))
        maybe_fill('input[type="email"]',          answers.get("email"))
        maybe_fill('input[type="tel"]',            answers.get("phone"))

        # Fill visible textareas with reasonable defaults
        for t in page.locator("textarea").all():
            ph = (t.get_attribute("placeholder") or "").lower()
            text = answers.get("why_me")
            if "authorization" in ph or "visa" in ph:
                text = answers.get("work_auth", text)
            elif "salary" in ph or "compensation" in ph:
                text = answers.get("salary", text)
            if text:
                t.fill(text)

        # Click a submit-like button
        for sel in [
            'button:has-text("Submit")',
            'button:has-text("Apply")',
            'button[type="submit"]',
            'input[type="submit"]',
        ]:
            if page.locator(sel).count():
                page.click(sel)
                break

        page.wait_for_load_state("networkidle")

        # Try to capture any "thank you" / confirmation text
        conf = page.locator('text=/thank you|application submitted|confirmation/i').first
        confirmation = (conf.text_content() or "").strip() if conf and conf.is_visible() else ""

        browser.close()
        return confirmation  # ✅ make sure this is spelled correctly and last

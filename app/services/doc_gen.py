from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
from playwright.sync_api import sync_playwright

TEMPLATES = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "xml"])
)

def render_html(template_name: str, context: dict) -> str:
    tpl = TEMPLATES.get_template(template_name)
    return tpl.render(**context)

def html_to_pdf(html: str, out_path: str) -> str:
    # Write temp HTML
    tmp_path = Path(out_path).with_suffix(".html")
    tmp_path.write_text(html, encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html, wait_until="load")
        page.emulate_media(media="print")
        page.pdf(path=out_path, format="Letter", print_background=True, margin={
            "top":"0.5in","bottom":"0.5in","left":"0.5in","right":"0.5in"
        })
        browser.close()

    return out_path

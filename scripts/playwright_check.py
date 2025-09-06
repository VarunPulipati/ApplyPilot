# scripts/playwright_check.py
import sys, asyncio
from playwright.sync_api import sync_playwright

print("Platform:", sys.platform)
print("Policy BEFORE:", type(asyncio.get_event_loop_policy()).__name__)

if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        print("Policy SET to Selector")
    except Exception as e:
        print("Policy set error:", e)

print("Policy NOW:", type(asyncio.get_event_loop_policy()).__name__)

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page()
    page.goto("https://example.com", wait_until="domcontentloaded")
    print("Page title:", page.title())
    b.close()

print("Playwright OK")

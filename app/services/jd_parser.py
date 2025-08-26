"""
Fetch and parse basic job details.
Note: Each ATS has its own structure; this is a generic starter.
"""

import httpx
from bs4 import BeautifulSoup

async def fetch_job_details(url: str) -> dict:
    # Grab the HTML (follow redirects; many ATS links redirect)
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url, follow_redirects=True)
        r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    # Naive title guess: first H1/H2
    h = soup.find(["h1", "h2"])
    title = h.get_text(strip=True) if h else ""

    # Company/location extraction varies; fill in per-ATS later
    company = ""
    location = ""

    jd_text = soup.get_text(" ", strip=True)  # full text for keywording/tailoring later
    return {"title": title, "company": company, "location": location, "jd_text": jd_text}

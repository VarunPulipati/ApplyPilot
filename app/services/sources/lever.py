from typing import List, Dict
import httpx

# Public JSON API: https://api.lever.co/v0/postings/{company}?mode=json
async def fetch_lever_company_jobs(company: str) -> List[Dict]:
    url = f"https://api.lever.co/v0/postings/{company}?mode=json"
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url)
        r.raise_for_status()
    data = r.json()
    results = []
    for j in data:
        results.append({
            "source": "lever",
            "company": j.get("categories", {}).get("team", "") or company,
            "title": j.get("text", ""),
            "location": j.get("categories", {}).get("location", ""),
            "url": j.get("hostedUrl", ""),
            "ats_type": "lever",
        })
    return results

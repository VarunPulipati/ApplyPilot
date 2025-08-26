from typing import List, Dict
import httpx

# Public JSON API: https://boards-api.greenhouse.io/v1/boards/{company}/jobs
async def fetch_greenhouse_company_jobs(company: str) -> List[Dict]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs"
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url)
        r.raise_for_status()
    data = r.json().get("jobs", [])
    results = []
    for j in data:
        results.append({
            "source": "greenhouse",
            "company": j.get("departments", [{}])[0].get("name", "") or company,
            "title": j.get("title", ""),
            "location": (j.get("location") or {}).get("name", ""),
            "url": j.get("absolute_url", ""),
            "ats_type": "greenhouse",
        })
    return results

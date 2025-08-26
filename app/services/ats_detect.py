"""
Very simple ATS detection by URL.
Expand with page-scan heuristics later.
"""

def detect_ats(url: str) -> str:
    u = url.lower()
    if "greenhouse.io" in u:
        return "greenhouse"
    if "lever.co" in u:
        return "lever"
    if "ashbyhq.com" in u:
        return "ashby"
    if "workable.com" in u:
        return "workable"
    return "unknown"

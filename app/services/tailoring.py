# app/services/tailoring.py
from __future__ import annotations
from typing import List, Dict, Any
from .ai import chat_json, chat_text

RESUME_SYSTEM = (
    "You are a resume writer that tailors content ONLY from the provided profile "
    "and experience bank. Never invent companies, titles, dates, or metrics."
)

ANSWER_SYSTEM = (
    "You answer job application questions truthfully and concisely (3–5 sentences), "
    "using ONLY the facts in 'profile' and 'experience bank'. If details are missing, "
    "stay general and skills-focused. Do NOT invent past employers or dates."
)

def generate_resume_context(profile: Dict[str, Any], jd_text: str, experience_bank: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Returns dict for templates/resume.html.j2:
    name, email, phone, location, summary, skills[list], experience[list of {role,company,years,bullets[list]}]
    """
    exp_text = "\n".join([f"- {x.get('base_answer','')}" for x in experience_bank])
    user = f"""
PROFILE:
name: {profile.get('name','')}
email: {profile.get('email','')}
phone: {profile.get('phone','')}
location: {profile.get('location','')}
core_skills: {', '.join(profile.get('skills', []))}

EXPERIENCE BANK (verbatim):
{exp_text}

JOB DESCRIPTION (verbatim):
{jd_text}

Return strict JSON with:
{{
  "summary": "one short paragraph",
  "skills": ["skill1","skill2","..."],
  "experience": [
    {{"role":"","company":"","years":"","bullets":["",""]}},
    ...
  ]
}}
"""
    data = chat_json(RESUME_SYSTEM, user)
    return {
        "name": profile.get("name","Your Name"),
        "email": profile.get("email","you@example.com"),
        "phone": profile.get("phone","+1-555-000-0000"),
        "location": profile.get("location",""),
        "summary": data.get("summary",""),
        "skills": data.get("skills", profile.get("skills", [])),
        "experience": data.get("experience", []),
    }

def draft_answers(questions: List[str], profile: Dict[str, Any], experience_bank: List[Dict[str,str]], jd_text: str) -> Dict[str,str]:
    exp_text = "\n".join([f"- {x.get('base_answer','')}" for x in experience_bank])
    result: Dict[str,str] = {}
    for q in questions:
        user = f"""
PROFILE:
{profile}

EXPERIENCE BANK (verbatim):
{exp_text}

JOB DESCRIPTION (verbatim):
{jd_text}

QUESTION:
{q}

Write a concise answer (3–5 sentences). Use ONLY what's above. If specifics are missing, keep it truthful and general (skills, impact, approach).
"""
        ans = chat_text(ANSWER_SYSTEM, user) or "I will tailor my impact based on the role’s needs; details available on request."
        result[q] = ans
    return result

def standard_answers(profile: Dict[str,str]) -> Dict[str,str]:
    first, *rest = (profile.get("name","Your Name").split() or ["Your"])
    last = " ".join(rest) or "Name"
    return {
        "first_name": first,
        "last_name": last,
        "email": profile.get("email","you@example.com"),
        "phone": profile.get("phone","+1-555-000-0000"),
    }

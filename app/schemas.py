"""
Pydantic schemas for request/response payloads.
"""

from pydantic import BaseModel


class ProfileCreate(BaseModel):
    name: str
    resume_path: str = ""
    portfolio_url: str = ""
    tags: str = ""


class ProfileOut(ProfileCreate):
    id: int

    class Config:
        from_attributes = True  # allow ORM-to-Pydantic conversion

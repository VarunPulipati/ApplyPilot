# app/schemas.py
from pydantic import BaseModel

class ProfileCreate(BaseModel):
    name: str
    email: str = ""
    phone: str = ""
    location: str = ""
    skills_csv: str = ""
    resume_path: str = ""

class ProfileOut(ProfileCreate):
    id: int
    class Config: from_attributes = True

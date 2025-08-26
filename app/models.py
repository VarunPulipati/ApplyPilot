"""
SQLAlchemy ORM models for the MVP: Profile, QABank, Job, Application.
Keep them simple for now; extend as features grow.
"""

from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


class Profile(Base):
    """
    A user's reusable resume/profile variant.
    Example: "ds-core", "de-azure".
    """
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120))
    resume_path: Mapped[str] = mapped_column(String(512), default="")   # path to DOCX or PDF
    portfolio_url: Mapped[str] = mapped_column(String(512), default="")
    tags: Mapped[str] = mapped_column(String(256), default="")          # comma-separated MVP


class QABank(Base):
    """
    Bank of base answers to common app questions.
    These are adapted per job (never invented).
    """
    __tablename__ = "qa_bank"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    qa_pack_id: Mapped[str] = mapped_column(String(120), default="default")
    question: Mapped[str] = mapped_column(Text)
    base_answer: Mapped[str] = mapped_column(Text)
    tags: Mapped[str] = mapped_column(String(256), default="")


class Job(Base):
    """
    Imported job posting (one row per URL).
    fields_schema can capture discovered form fields later.
    """
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String(1000))
    source: Mapped[str] = mapped_column(String(120), default="")
    company: Mapped[str] = mapped_column(String(200), default="")
    title: Mapped[str] = mapped_column(String(200), default="")
    location: Mapped[str] = mapped_column(String(200), default="")
    ats_type: Mapped[str] = mapped_column(String(80), default="")
    fields_schema: Mapped[dict] = mapped_column(JSON, default={})  # structure varies by ATS
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Application(Base):
    """
    One application attempt (linked to a Job + Profile).
    Stores status, confirmation number, and doc versions.
    """
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"))
    qa_pack_id: Mapped[str] = mapped_column(String(120), default="default")

    status: Mapped[str] = mapped_column(String(60), default="created")  # created|submitted|failed
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    confirmation_number: Mapped[str] = mapped_column(String(120), default="")

    resume_version: Mapped[str] = mapped_column(String(120), default="")
    cover_letter_version: Mapped[str] = mapped_column(String(120), default="")
    notes: Mapped[str] = mapped_column(Text, default="")

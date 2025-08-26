"""
SQLAlchemy engine/session setup and a FastAPI dependency to get a DB session.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings

# Create a DB engine from config (SQLite by default for easy local dev)
engine = create_engine(settings.database_url, future=True)

# Session factory (autoflush False avoids surprising implicit writes)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)

# Declarative Base for models to inherit from
class Base(DeclarativeBase):
    pass


def get_db():
    """
    FastAPI dependency that yields a SQLAlchemy session.
    Ensures the session is closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

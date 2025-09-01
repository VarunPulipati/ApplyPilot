from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..database import get_db
from ..models import QABank

router = APIRouter(prefix="/qa", tags=["qa"])

class QAIn(BaseModel):
    qa_pack_id: str = "default"
    question: str
    base_answer: str
    tags: str = ""   # e.g., "experience, sql, airflow"

@router.post("")
def add_qa(body: QAIn, db: Session = Depends(get_db)):
    row = QABank(**body.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return {"id": row.id}

@router.get("")
def list_qa(db: Session = Depends(get_db)):
    rows = db.query(QABank).order_by(QABank.id.desc()).all()
    return [{"id":r.id,"question":r.question,"tags":r.tags} for r in rows]

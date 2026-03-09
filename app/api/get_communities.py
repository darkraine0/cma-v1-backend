from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import Plan
from pydantic import BaseModel

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class CommunityNameOut(BaseModel):
    id: int
    name: str

@router.get("/get_communities", response_model=list[CommunityNameOut])
def get_communities(db: Session = Depends(get_db)):
    """Return all distinct community names that have at least one plan in the plans table."""
    rows = db.query(Plan.community).distinct().filter(Plan.community.isnot(None)).filter(Plan.community != "").order_by(Plan.community).all()
    return [CommunityNameOut(id=i + 1, name=name) for i, (name,) in enumerate(rows)]

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import CommunityName
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
    plan: int
    now: int


@router.get("/get_communities", response_model=list[CommunityNameOut])
def get_communities(db: Session = Depends(get_db)):
    """Return all rows from the community_names table."""
    rows = db.query(CommunityName).order_by(CommunityName.name).all()
    return [
        CommunityNameOut(id=row.id, name=row.name, plan=row.plan, now=row.now)
        for row in rows
    ]

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import Plan, PriceHistory
from app.models.plan import PlanWithChangeFlag
from datetime import datetime, timedelta

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/plans", response_model=list[PlanWithChangeFlag])
def get_plans(db: Session = Depends(get_db)):
    plans = db.query(Plan).all()
    since = datetime.utcnow() - timedelta(hours=24)
    recent_changes = db.query(PriceHistory).filter(PriceHistory.changed_at >= since).all()
    changed_plan_ids = {ph.plan_id for ph in recent_changes}
    result = []
    for plan in plans:
        # Only include plans with all required fields present (sqft and stories can be None for some scrapers)
        if not (plan.plan_name is not None and plan.price is not None and plan.company and plan.community):
            continue
        result.append(PlanWithChangeFlag(
            plan_name=plan.plan_name,
            price=plan.price,
            sqft=plan.sqft,
            stories=plan.stories,
            price_per_sqft=plan.price_per_sqft,
            last_updated=plan.last_updated,
            company=plan.company,
            community=plan.community,
            type=plan.type,
            address=plan.address,
            price_changed_recently=plan.id in changed_plan_ids
        ))
    return result 
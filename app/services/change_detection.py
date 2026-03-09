from sqlalchemy.orm import Session
from app.db.models import Plan, PriceHistory, CommunityName
from datetime import datetime, timedelta

def ensure_community_names(db: Session, community_names: set):
    """Insert any new community names into the community_names table."""
    for name in community_names:
        if name and db.query(CommunityName).filter(CommunityName.name == name).first() is None:
            db.add(CommunityName(name=name))

def sync_community_names_from_plans(db: Session):
    """Ensure community_names table has every distinct community that exists in the plans table."""
    distinct = db.query(Plan.community).distinct().all()
    for (name,) in distinct:
        if name and db.query(CommunityName).filter(CommunityName.name == name).first() is None:
            db.add(CommunityName(name=name))
    db.commit()

def detect_and_update_changes(db: Session, new_plans: list):
    """Delete all plans (and price history) for the communities in this batch, then insert new_plans."""
    if not new_plans:
        return
    communities = {p.get("community") for p in new_plans if p.get("community")}
    # Ensure each community name exists in community_names table
    ensure_community_names(db, communities)
    # Delete price history for plans in those communities (FK first)
    plan_ids = [row[0] for row in db.query(Plan.id).filter(Plan.community.in_(communities)).all()]
    if plan_ids:
        db.query(PriceHistory).filter(PriceHistory.plan_id.in_(plan_ids)).delete(
            synchronize_session=False
        )
    # Delete all plans for those communities
    db.query(Plan).filter(Plan.community.in_(communities)).delete(synchronize_session=False)
    # Insert all new_plans
    for plan_data in new_plans:
        plan = Plan(
            plan_name=plan_data["plan_name"],
            price=plan_data["price"],
            sqft=plan_data.get("sqft"),
            stories=plan_data.get("stories"),
            price_per_sqft=plan_data.get("price_per_sqft"),
            last_updated=datetime.utcnow(),
            company=plan_data["company"],
            community=plan_data["community"],
            type=plan_data.get("type", "plan"),
            beds=plan_data.get("beds", ""),
            baths=plan_data.get("baths", ""),
            address=plan_data.get("address", ""),
            design_number=plan_data.get("design_number", ""),
        )
        db.add(plan)
    db.commit()

def get_recent_price_changes(db: Session, within_minutes: int = 1440):
    since = datetime.utcnow() - timedelta(minutes=within_minutes)
    return db.query(PriceHistory).filter(PriceHistory.changed_at >= since).all() 
from sqlalchemy.orm import Session
from app.db.models import Plan, PriceHistory, CommunityName
from datetime import datetime, timedelta

def _update_community_counts(db: Session):
    """Set plan and now counts on each CommunityName from the plans table."""
    from sqlalchemy import func
    # Count per community: type='plan' and type='now'
    for row in db.query(CommunityName).all():
        plan_count = db.query(func.count(Plan.id)).filter(
            Plan.community == row.name, Plan.type == "plan"
        ).scalar() or 0
        now_count = db.query(func.count(Plan.id)).filter(
            Plan.community == row.name, Plan.type == "now"
        ).scalar() or 0
        row.plan = plan_count
        row.now = now_count
    db.commit()

def sync_community_names_from_plans(db: Session):
    """Ensure community_names table has every distinct community that exists in the plans table, and update plan/now counts."""
    # Delete all existing community_names, then rebuild from plans
    db.query(CommunityName).delete()
    distinct = db.query(Plan.community).distinct().all()
    for (name,) in distinct:
        if name and db.query(CommunityName).filter(CommunityName.name == name).first() is None:
            db.add(CommunityName(name=name, plan=0, now=0))
    db.commit()
    _update_community_counts(db)

def detect_and_update_changes(db: Session, new_plans: list):
    """Delete all plans (and price history) for the communities in this batch, then insert new_plans."""
    if not new_plans:
        return
    communities = {p.get("community") for p in new_plans if p.get("community")}
    # Delete existing data only when we have communities (avoid IN () with empty set)
    if communities:
        plan_ids = [row[0] for row in db.query(Plan.id).filter(Plan.community.in_(communities)).all()]
        if plan_ids:
            db.query(PriceHistory).filter(PriceHistory.plan_id.in_(plan_ids)).delete(
                synchronize_session=False
            )
        db.query(Plan).filter(Plan.community.in_(communities)).delete(synchronize_session=False)
    # Insert new_plans (use .get() so missing keys don't crash)
    for plan_data in new_plans:
        community = plan_data.get("community") or ""
        company = plan_data.get("company") or ""
        if not community or not company:
            continue
        plan = Plan(
            plan_name=plan_data.get("plan_name"),
            price=plan_data.get("price"),
            sqft=plan_data.get("sqft"),
            stories=plan_data.get("stories"),
            price_per_sqft=plan_data.get("price_per_sqft"),
            last_updated=datetime.utcnow(),
            company=company,
            community=community,
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
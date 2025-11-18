from sqlalchemy.orm import Session
from app.db.models import Plan, PriceHistory
from datetime import datetime, timedelta

def detect_and_update_changes(db: Session, new_plans: list):
    for plan_data in new_plans:
        # Require company, community, and type for uniqueness (since same plan can be "now" and "plan")
        plan = db.query(Plan).filter_by(
            plan_name=plan_data['plan_name'],
            company=plan_data['company'],
            community=plan_data['community'],
            type=plan_data.get('type', 'plan')
        ).first()
        if plan:
            if plan.price != plan_data['price']:
                # Record price change
                price_history = PriceHistory(
                    plan_id=plan.id,
                    old_price=plan.price,
                    new_price=plan_data['price'],
                    changed_at=datetime.utcnow()
                )
                db.add(price_history)
                plan.price = plan_data['price']
                plan.last_updated = datetime.utcnow()
                # Update type if it changed
                if 'type' in plan_data:
                    plan.type = plan_data['type']
                # Update other fields if they changed
                if 'beds' in plan_data:
                    plan.beds = plan_data['beds']
                if 'baths' in plan_data:
                    plan.baths = plan_data['baths']
                if 'address' in plan_data:
                    plan.address = plan_data['address']
                if 'design_number' in plan_data:
                    plan.design_number = plan_data['design_number']
        else:
            plan = Plan(
                plan_name=plan_data['plan_name'],
                price=plan_data['price'],
                sqft=plan_data['sqft'],
                stories=plan_data['stories'],
                price_per_sqft=plan_data['price_per_sqft'],
                last_updated=datetime.utcnow(),
                company=plan_data['company'],
                community=plan_data['community'],
                type=plan_data.get('type', 'plan'),  # Default to 'plan' if not specified
                beds=plan_data.get('beds', ''),  # Add beds field
                baths=plan_data.get('baths', ''),  # Add baths field
                address=plan_data.get('address', ''),  # Add address field
                design_number=plan_data.get('design_number', '')  # Add design_number field
            )
            db.add(plan)
    db.commit()

def get_recent_price_changes(db: Session, within_minutes: int = 1440):
    since = datetime.utcnow() - timedelta(minutes=within_minutes)
    return db.query(PriceHistory).filter(PriceHistory.changed_at >= since).all() 
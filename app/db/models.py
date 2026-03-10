from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class CommunityName(Base):
    """Table of community names (one row per community)."""
    __tablename__ = "community_names"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    plan = Column(Integer, default=0, nullable=False)   # count of plans where type='plan'
    now = Column(Integer, default=0, nullable=False)    # count of plans where type='now'
    created_at = Column(DateTime, default=datetime.utcnow)


class Plan(Base):
    __tablename__ = "plans"
    id = Column(Integer, primary_key=True, index=True)
    plan_name = Column(String, index=True)
    price = Column(Float)
    sqft = Column(Integer)
    stories = Column(String)
    price_per_sqft = Column(Float)
    last_updated = Column(DateTime, default=datetime.utcnow)
    company = Column(String, nullable=False)
    community = Column(String, nullable=False)
    type = Column(String, nullable=False, default="plan")  # "plan" or "now"
    beds = Column(String)  # Number of bedrooms
    baths = Column(String)  # Number of bathrooms
    address = Column(String)  # Full address for "now" items
    design_number = Column(String)  # Design number/model
    price_histories = relationship("PriceHistory", back_populates="plan")

class PriceHistory(Base):
    __tablename__ = "price_history"
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"))
    old_price = Column(Float)
    new_price = Column(Float)
    changed_at = Column(DateTime, default=datetime.utcnow)
    plan = relationship("Plan", back_populates="price_histories") 
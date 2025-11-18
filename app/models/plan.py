from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PlanBase(BaseModel):
    plan_name: str
    price: float
    sqft: Optional[int] = None
    stories: Optional[str] = None
    price_per_sqft: Optional[float] = None
    last_updated: datetime
    company: str
    community: str
    type: str
    address: Optional[str] = None

class PlanWithChangeFlag(PlanBase):
    price_changed_recently: bool

    class Config:
        from_attributes = True 
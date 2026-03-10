from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from .models import Base, CommunityName, Plan, PriceHistory  # import all models so create_all creates every table

SQLALCHEMY_DATABASE_URL = "sqlite:///./homes.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    # Add plan/now columns to community_names if they don't exist (e.g. existing DB)
    with engine.connect() as conn:
        for col in ("plan", "now"):
            try:
                conn.execute(text(f"ALTER TABLE community_names ADD COLUMN {col} INTEGER DEFAULT 0 NOT NULL"))
                conn.commit()
            except Exception:
                conn.rollback()
                pass  # column likely already exists 
"""
SQLAlchemy engine + session setup.

Run this file directly to create all tables from the models:
    python -m app.database
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

# Neon/Supabase connection strings come as a plain "postgresql://" URL, which
# tells SQLAlchemy to use the (older) psycopg2 driver. This project installs
# psycopg 3 instead (better prebuilt-wheel support on newer Python), so force
# that dialect here regardless of how the URL is written.
db_url = settings.database_url
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    # Import all models here so Base.metadata knows about every table
    # before create_all() is called.
    from app.models import citizen, staff, report, status_log  # noqa: F401

    Base.metadata.create_all(bind=engine)
    print("All tables created successfully.")

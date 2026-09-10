"""
SQLAlchemy engine + session setup.

Run this file directly to create all tables from the models:
    python -m app.database
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

engine = create_engine(settings.database_url)
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

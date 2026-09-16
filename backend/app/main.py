import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from sqlalchemy import text

from app.config import settings
from app.database import Base, engine
from app.models import citizen, staff as staff_model, report, status_log  # noqa: F401
from app.routers import citizens, reports, staff, admin

app = FastAPI(
    title="Local Civic Problem Reporting System",
    description="E-Governance lab project — citizens report local infrastructure "
    "problems, staff/admin review and resolve them.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Make sure the upload folder exists, then serve uploaded photos as static files
os.makedirs(settings.upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

app.include_router(citizens.router)
app.include_router(reports.router)
app.include_router(staff.router)
app.include_router(admin.router)


@app.on_event("startup")
def create_tables_if_missing():
    # Safe to run every time: create_all() only creates tables that don't
    # already exist yet. This means a fresh deploy (e.g. on Render, where
    # you can't easily run `python -m app.database` by hand) sets itself
    # up automatically on first boot.
    Base.metadata.create_all(bind=engine)

    # create_all() never alters an EXISTING table, so columns added to a
    # model after the table already exists (like these) need an explicit,
    # idempotent migration — also run automatically since there's no shell
    # access on Render's free tier to run one by hand.
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE reports ADD COLUMN IF NOT EXISTS photo_data BYTEA"
        ))
        conn.execute(text(
            "ALTER TABLE reports ADD COLUMN IF NOT EXISTS photo_content_type VARCHAR(50)"
        ))
        conn.execute(text(
            "ALTER TABLE staff ADD COLUMN IF NOT EXISTS disabled BOOLEAN NOT NULL DEFAULT FALSE"
        ))


@app.get("/")
def root():
    return {"status": "ok", "service": "Local Civic Problem Reporting System API"}


@app.get("/health")
def health():
    return {"status": "ok"}

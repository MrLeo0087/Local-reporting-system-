import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
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


@app.get("/")
def root():
    return {"status": "ok", "service": "Local Civic Problem Reporting System API"}


@app.get("/health")
def health():
    return {"status": "ok"}

"""
Helper for processing an uploaded report photo.

Keeps things simple: validate extension + size, shrink/compress it, and
return the final bytes + content type + a filename (for record-keeping).
The bytes go straight into the database (see models/report.py) rather than
onto local disk — Render's free-tier disk is wiped on every restart, so
anything written there doesn't survive.
"""
import io
import os
import uuid

from fastapi import UploadFile, HTTPException
from PIL import Image

from app.config import settings

MAX_DIMENSION = 1600  # px, longest side — keeps photos reasonably small

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}


def process_report_photo(photo: UploadFile) -> tuple[bytes, str, str]:
    """Returns (image_bytes, content_type, filename)."""
    _, ext = os.path.splitext(photo.filename or "")
    ext = ext.lower()

    if ext not in ALLOWED_EXTENSIONS or photo.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only JPG and PNG image files are accepted.",
        )

    max_bytes = settings.max_upload_mb * 1024 * 1024
    contents = photo.file.read()
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"Photo is too large. Maximum size is {settings.max_upload_mb}MB.",
        )

    filename = f"{uuid.uuid4().hex}{ext}"
    content_type = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"

    # Best-effort compression: shrink oversized images and re-encode with
    # moderate quality. If anything goes wrong (unusual file, etc.) fall back
    # to the original bytes untouched rather than failing the upload.
    try:
        image = Image.open(io.BytesIO(contents))
        image.thumbnail((MAX_DIMENSION, MAX_DIMENSION))
        buffer = io.BytesIO()
        if ext in (".jpg", ".jpeg"):
            if image.mode != "RGB":
                image = image.convert("RGB")
            image.save(buffer, format="JPEG", quality=85, optimize=True)
        else:
            image.save(buffer, format="PNG")
        processed = buffer.getvalue()
    except Exception:
        processed = contents

    return processed, content_type, filename

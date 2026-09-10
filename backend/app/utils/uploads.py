"""
Helper for saving an uploaded report photo to disk.

Keeps things simple: validate extension + size, generate a unique filename,
write the bytes, return the relative path to store in the DB.
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


def save_report_photo(photo: UploadFile) -> str:
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

    os.makedirs(settings.upload_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(settings.upload_dir, filename)

    # Best-effort compression: shrink oversized images and re-encode with
    # moderate quality. If anything goes wrong (unusual file, etc.) fall back
    # to saving the original bytes untouched rather than failing the upload.
    try:
        image = Image.open(io.BytesIO(contents))
        image.thumbnail((MAX_DIMENSION, MAX_DIMENSION))
        save_kwargs = {"quality": 85, "optimize": True} if ext in (".jpg", ".jpeg") else {}
        if ext in (".jpg", ".jpeg") and image.mode != "RGB":
            image = image.convert("RGB")
        image.save(file_path, **save_kwargs)
    except Exception:
        with open(file_path, "wb") as f:
            f.write(contents)

    # Path stored in the DB / returned to the frontend, servable at /uploads/<filename>
    return f"/uploads/{filename}"

import io, logging, uuid
from typing import Annotated
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.database.connection import get_db
from app.models.image import ImageAsset
from app.schemas.research import ImageMetadataOut, ImageOut
from app.services.image_service import ImageValidationError, create_thumbnail, inspect_image
from app.services.storage_service import STORAGE, StorageError, store_image
from app.utils.hashing import sha256_hex
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)
MAX_BYTES = settings.max_upload_bytes

@router.get("/api/v1/images/{image_id}/thumbnail")
def image_file(image_id: str, db: Session = Depends(get_db), size: Annotated[int, Query(ge=32, le=2400)] = 160):
    asset = db.get(ImageAsset, image_id)
    if asset is None:
        raise HTTPException(404, detail={"code":"image_not_found","message":"Image was not found."})
    path = Path(asset.storage_path).resolve()
    if path.parent != STORAGE or not path.is_file():
        raise HTTPException(404, detail={"code":"image_not_found","message":"Image file was not found."})
    try:
        thumbnail = create_thumbnail(path, size=size)
    except (OSError, UnidentifiedImageError, ValueError):
        logger.exception("Unable to produce image thumbnail for %s", image_id)
        raise HTTPException(500, detail={"code":"thumbnail_unavailable","message":"An image preview could not be generated."}) from None
    return Response(content=thumbnail, media_type="image/jpeg", headers={"Content-Disposition":"inline; filename=preview.jpg", "Cache-Control":"private, max-age=300"})

@router.get("/api/v1/images/{image_id}/metadata", response_model=ImageMetadataOut)
def image_metadata(image_id: str, db: Session = Depends(get_db)):
    asset = db.get(ImageAsset, image_id)
    if asset is None:
        raise HTTPException(404, detail={"code":"image_not_found","message":"Image was not found."})
    try:
        with Image.open(asset.storage_path) as im:
            exif = im.getexif()
            from PIL.ExifTags import TAGS
            metadata = {TAGS.get(k, str(k)): str(v)[:300] for k, v in list(exif.items())[:100]}
    except Exception:
        logger.warning("Unable to parse EXIF metadata for image %s", image_id, exc_info=True)
        metadata = {}
    return {"id": asset.id, "original_filename": asset.original_filename, "mime_type": asset.mime_type, "file_size": asset.file_size, "width": asset.width, "height": asset.height, "sha256": asset.sha256, "created_at": asset.created_at, "exif": metadata, "provenance": "No provenance manifest was detected or checked.", "ai_detection": "Not yet analyzed"}

@router.post("/api/v1/images/upload", response_model=ImageOut, status_code=201)
def upload_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        contents = file.file.read(MAX_BYTES + 1)
    except OSError:
        logger.exception("Unable to read uploaded image stream")
        raise HTTPException(400, detail={"code":"upload_read_failed","message":"The uploaded image could not be read."}) from None
    if len(contents) > MAX_BYTES:
        raise HTTPException(413, detail={"code":"file_too_large","message":f"Image exceeds the {settings.max_upload_size_mb} MB upload limit."})
    try:
        fmt, mime_type, width, height = inspect_image(contents)
    except ImageValidationError as exc:
        raise HTTPException(exc.status_code, detail={"code": exc.code, "message": exc.message}) from None
    digest = sha256_hex(contents)
    existing = db.scalar(select(ImageAsset).where(ImageAsset.sha256 == digest))
    if existing is not None:
        return existing
    image_id = str(uuid.uuid4())
    try:
        stored, target = store_image(contents, fmt)
    except StorageError:
        logger.exception("Image storage failed")
        raise HTTPException(503, detail={"code":"storage_unavailable","message":"Image storage is temporarily unavailable."}) from None
    safe_name = Path(file.filename or "image").name[:255]
    asset = ImageAsset(id=image_id, original_filename=safe_name, stored_filename=stored, mime_type=mime_type, file_size=len(contents), width=width, height=height, sha256=digest, storage_path=str(target))
    try:
        db.add(asset); db.commit(); db.refresh(asset)
    except Exception:
        db.rollback()
        try:
            target.unlink(missing_ok=True)
        except OSError:
            logger.exception("Unable to remove image file after database failure")
        raise
    return asset

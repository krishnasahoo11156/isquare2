import io, os, uuid
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.image import ImageAsset
from app.schemas.research import ImageOut
from app.services.image_service import ImageValidationError, inspect_image
from app.services.storage_service import STORAGE, store_image
from app.utils.hashing import sha256_hex

router = APIRouter()
MAX_BYTES = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10")) * 1024 * 1024

@router.get("/api/v1/images/{image_id}/thumbnail")
def image_file(image_id: str, db: Session = Depends(get_db)):
    asset = db.get(ImageAsset, image_id)
    if asset is None:
        raise HTTPException(404, detail={"code":"image_not_found","message":"Image was not found."})
    path = Path(asset.storage_path).resolve()
    if path.parent != STORAGE or not path.is_file():
        raise HTTPException(404, detail={"code":"image_not_found","message":"Image file was not found."})
    return FileResponse(path, media_type=asset.mime_type, filename=asset.original_filename)

@router.get("/api/v1/images/{image_id}/metadata")
def image_metadata(image_id: str, db: Session = Depends(get_db)):
    asset = db.get(ImageAsset, image_id)
    if asset is None:
        raise HTTPException(404, detail={"code":"image_not_found","message":"Image was not found."})
    try:
        with Image.open(asset.storage_path) as im:
            exif = im.getexif()
            from PIL.ExifTags import TAGS
            metadata = {TAGS.get(k, str(k)): str(v)[:300] for k, v in exif.items()}
    except (OSError, UnidentifiedImageError):
        metadata = {}
    return {"id": asset.id, "original_filename": asset.original_filename, "mime_type": asset.mime_type, "file_size": asset.file_size, "width": asset.width, "height": asset.height, "sha256": asset.sha256, "created_at": asset.created_at, "exif": metadata, "provenance": "No provenance manifest was detected or checked.", "ai_detection": "Not yet analyzed"}

@router.post("/api/v1/images/upload", response_model=ImageOut, status_code=201)
def upload_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = file.file.read(MAX_BYTES + 1)
    if len(contents) > MAX_BYTES:
        raise HTTPException(413, detail={"code":"file_too_large","message":"Image exceeds the 10 MB upload limit."})
    try:
        fmt, mime_type, width, height = inspect_image(contents)
    except ImageValidationError as exc:
        raise HTTPException(exc.status_code, detail={"code": exc.code, "message": exc.message}) from None
    image_id = str(uuid.uuid4())
    stored, target = store_image(contents, fmt)
    safe_name = Path(file.filename or "image").name[:255]
    asset = ImageAsset(id=image_id, original_filename=safe_name, stored_filename=stored, mime_type=mime_type, file_size=len(contents), width=width, height=height, sha256=sha256_hex(contents), storage_path=str(target))
    try:
        db.add(asset); db.commit(); db.refresh(asset)
    except Exception:
        target.unlink(missing_ok=True); db.rollback(); raise
    return asset

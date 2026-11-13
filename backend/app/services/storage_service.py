import os, uuid
from pathlib import Path

STORAGE = Path(os.getenv("STORAGE_DIR", "./storage/uploads")).resolve()
EXTENSIONS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}

def store_image(contents: bytes, image_format: str) -> tuple[str, Path]:
    stored_filename = f"{uuid.uuid4().hex}{EXTENSIONS[image_format]}"
    STORAGE.mkdir(parents=True, exist_ok=True)
    target = (STORAGE / stored_filename).resolve()
    if target.parent != STORAGE:
        raise ValueError("Invalid storage target")
    target.write_bytes(contents)
    return stored_filename, target

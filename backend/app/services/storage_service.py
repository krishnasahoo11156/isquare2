import uuid
from pathlib import Path
from app.core.config import settings

STORAGE = settings.storage_dir
EXTENSIONS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}

class StorageError(OSError):
    pass

def store_image(contents: bytes, image_format: str) -> tuple[str, Path]:
    stored_filename = f"{uuid.uuid4().hex}{EXTENSIONS[image_format]}"
    target = STORAGE / stored_filename
    try:
        STORAGE.mkdir(parents=True, exist_ok=True)
        target = target.resolve()
        if target.parent != STORAGE:
            raise StorageError("Invalid storage target")
        with target.open("xb") as output:
            output.write(contents)
        return stored_filename, target
    except StorageError:
        raise
    except OSError as exc:
        try:
            target.unlink(missing_ok=True)
        except OSError:
            pass
        raise StorageError("Image storage is unavailable") from exc

import io
from pathlib import Path
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_PIXELS = 40_000_000
MIME_TYPES = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}

class ImageValidationError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)

def inspect_image(contents: bytes) -> tuple[str, str, int, int]:
    try:
        with Image.open(io.BytesIO(contents)) as probe:
            image_format = probe.format
            width, height = probe.size
            if image_format not in MIME_TYPES:
                raise ImageValidationError(415, "unsupported_image", "Upload a JPEG, PNG, or WEBP image.")
            if width < 1 or height < 1 or width * height > MAX_PIXELS:
                raise ImageValidationError(422, "invalid_dimensions", "Image dimensions are invalid or exceed 40 megapixels.")
            probe.verify()
        with Image.open(io.BytesIO(contents)) as decoded:
            decoded.load()
            if decoded.format != image_format:
                raise ImageValidationError(422, "invalid_image", "Image content could not be verified.")
        return image_format, MIME_TYPES[image_format], width, height
    except ImageValidationError:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ImageValidationError(422, "invalid_image", "The uploaded file is not a valid supported image.") from None

def create_thumbnail(path: Path, size: int = 160) -> bytes:
    output = io.BytesIO()
    with Image.open(path) as source:
        source = ImageOps.exif_transpose(source)
        source.thumbnail((size, size), Image.Resampling.LANCZOS)
        if source.mode not in ("RGB", "RGBA"):
            source = source.convert("RGBA" if "transparency" in source.info else "RGB")
        if source.mode == "RGBA":
            background = Image.new("RGB", source.size, "white")
            background.paste(source, mask=source.getchannel("A"))
            source = background
        source.save(output, format="JPEG", quality=82, optimize=True)
    return output.getvalue()

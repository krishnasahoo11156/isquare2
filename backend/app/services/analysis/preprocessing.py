from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps, ImageStat

from app.core.config import settings


@dataclass
class PreparedImage:
    image: Image.Image
    original_width: int
    original_height: int
    width: int
    height: int
    operations: list[str]

    def close(self) -> None:
        self.image.close()


def prepare_image(path: Path) -> PreparedImage:
    """Decode to bounded RGB pixels, normalize EXIF orientation, preserve source file."""
    with Image.open(path) as source:
        oriented = ImageOps.exif_transpose(source)
        oriented.load()
        original_width, original_height = oriented.size
        rgb = oriented.convert("RGB")
        oriented.close()
    operations = ["exif_orientation_normalized", "rgb_normalized"]
    rgb.thumbnail((settings.analysis_max_dimension, settings.analysis_max_dimension), Image.Resampling.LANCZOS)
    if rgb.size != (original_width, original_height):
        operations.append("downscaled_to_resource_limit")
    return PreparedImage(rgb, original_width, original_height, rgb.width, rgb.height, operations)


def choose_ocr_image(prepared: PreparedImage) -> tuple[Image.Image, list[str]]:
    """Select one restrained OCR variant from image luminance statistics."""
    gray = ImageOps.grayscale(prepared.image)
    stats = ImageStat.Stat(gray)
    contrast = stats.stddev[0]
    if contrast < 42:
        enhanced = ImageEnhance.Contrast(gray).enhance(1.5)
        gray.close()
        return enhanced, ["grayscale", "contrast_adjusted_low_contrast"]
    return gray, ["grayscale"]

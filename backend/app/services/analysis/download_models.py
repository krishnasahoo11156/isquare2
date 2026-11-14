"""Explicitly download the small SSDLite detector weights; never called by API/worker startup."""
from pathlib import Path

from app.core.config import settings


def download_detector() -> Path:
    try:
        import torch
        from torchvision.models.detection import SSDLite320_MobileNet_V3_Large_Weights
    except ImportError as exc:
        raise SystemExit("Install the optional CPU PyTorch and torchvision packages first; see docs/PHASE_03_MODELS.md") from exc
    weights = SSDLite320_MobileNet_V3_Large_Weights.COCO_V1
    settings.model_cache_dir.mkdir(parents=True, exist_ok=True)
    target = settings.model_cache_dir / "ssdlite320_mobilenet_v3_large-coco_v1.pth"
    if target.is_file():
        print(f"Weights already exist: {target}")
        return target
    temporary = target.with_suffix(".download")
    try:
        torch.hub.download_url_to_file(weights.url, str(temporary), hash_prefix=weights.url.rsplit("/", 1)[-1].split("-")[-1].split(".")[0], progress=True)
        temporary.replace(target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    print(f"Downloaded detector weights: {target} ({target.stat().st_size / (1024 * 1024):.1f} MiB)")
    return target


if __name__ == "__main__":
    download_detector()

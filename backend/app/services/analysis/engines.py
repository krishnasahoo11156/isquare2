import shutil
import time
import threading
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from app.core.config import settings
from app.services.analysis.preprocessing import PreparedImage, choose_ocr_image


class EngineUnavailable(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass
class OCRBlock:
    text: str
    confidence: float | None
    box: dict[str, int]
    sequence: int


@dataclass
class OCROutput:
    text: str
    language: str
    engine: str
    version: str
    duration_ms: int
    status: str
    blocks: list[OCRBlock] = field(default_factory=list)
    preprocessing: list[str] = field(default_factory=list)


@dataclass
class Detection:
    label: str
    confidence: float
    box: dict[str, int]
    model: str
    version: str


_detector_lock = threading.Lock()
_detector = None
_detector_meta = None


def _load_tesseract():
    try:
        import pytesseract
    except ImportError as exc:
        raise EngineUnavailable("ocr_dependency_missing", "Install the optional OCR dependencies and Tesseract as described in docs/PHASE_03_MODELS.md.") from exc
    configured = settings.tesseract_cmd
    executable = configured or shutil.which("tesseract")
    if not executable or (configured and not Path(configured).is_file()):
        raise EngineUnavailable("ocr_engine_missing", "Tesseract was not found. Install Tesseract 5 and configured language data; see docs/PHASE_03_MODELS.md.")
    pytesseract.pytesseract.tesseract_cmd = executable
    try:
        version = str(pytesseract.get_tesseract_version()).splitlines()[0]
        available = set(pytesseract.get_languages(config=""))
    except Exception as exc:
        raise EngineUnavailable("ocr_engine_unavailable", "Tesseract is installed but could not be initialized. Check its language data and path.") from exc
    languages = settings.ocr_language.split("+")
    if any(language not in available for language in languages):
        raise EngineUnavailable("ocr_language_unavailable", "One or more configured Tesseract language packs are missing.")
    return pytesseract, version


def run_ocr(prepared: PreparedImage) -> OCROutput:
    pytesseract, version = _load_tesseract()
    image, operations = choose_ocr_image(prepared)
    input_width, input_height = image.size
    started = time.perf_counter()
    try:
        data = pytesseract.image_to_data(image, lang=settings.ocr_language, output_type=pytesseract.Output.DICT,
                                         config="--psm 3", timeout=settings.ocr_timeout_seconds)
    except Exception as exc:
        raise EngineUnavailable("ocr_execution_failed", "Tesseract could not process this image.") from exc
    finally:
        image.close()
    elapsed = round((time.perf_counter() - started) * 1000)
    lines: dict[tuple[str, ...], list[str]] = {}
    blocks: list[OCRBlock] = []
    index = 0
    for i, raw_text in enumerate(data.get("text", [])):
        text = str(raw_text).strip()
        if not text:
            continue
        try:
            confidence_raw = float(data["conf"][i])
        except (ValueError, TypeError, IndexError):
            confidence_raw = -1
        confidence = confidence_raw / 100 if confidence_raw >= 0 else None
        if confidence is not None and confidence < 0.05:
            continue
        x, y = int(data["left"][i]), int(data["top"][i])
        width, height = int(data["width"][i]), int(data["height"][i])
        # Tesseract returns bounds on its preprocessing input. Scale them back to
        # the normalized analysis image coordinate space used by the frontend.
        sx, sy = prepared.width / input_width, prepared.height / input_height
        box = {"x": round(x * sx), "y": round(y * sy), "width": round(width * sx), "height": round(height * sy)}
        blocks.append(OCRBlock(text, confidence, box, index))
        line_key = tuple(str(data.get(field, [""] * (i + 1))[i]) for field in ("page_num", "block_num", "par_num", "line_num"))
        lines.setdefault(line_key, []).append(text)
        index += 1
    full_text = "\n".join(" ".join(line_words) for line_words in lines.values())
    return OCROutput(full_text, settings.ocr_language, "Tesseract", version, elapsed, "completed", blocks, operations)

def run_classifier(_prepared: PreparedImage):
    raise EngineUnavailable("classifier_not_configured", "No validated iSquare category classifier is installed. The generic ImageNet labels are not mapped to iSquare categories.")


def _load_detector():
    global _detector, _detector_meta
    with _detector_lock:
        if _detector is not None:
            return _detector, _detector_meta
        weights_path = settings.model_cache_dir / "ssdlite320_mobilenet_v3_large-coco_v1.pth"
        if not weights_path.is_file():
            raise EngineUnavailable("detector_weights_missing", "The SSDLite COCO weights are not installed. Run the explicit model download command in docs/PHASE_03_MODELS.md.")
        try:
            import torch
            import torchvision
            from torchvision.models.detection import ssdlite320_mobilenet_v3_large
            from torchvision.models.detection import SSDLite320_MobileNet_V3_Large_Weights
        except ImportError as exc:
            raise EngineUnavailable("detector_dependency_missing", "Install the optional CPU vision dependencies described in docs/PHASE_03_MODELS.md.") from exc
        try:
            torch.set_num_threads(1)
            weights = SSDLite320_MobileNet_V3_Large_Weights.COCO_V1
            model = ssdlite320_mobilenet_v3_large(weights=None, weights_backbone=None)
            state = torch.load(weights_path, map_location="cpu", weights_only=True)
            model.load_state_dict(state)
            model.eval()
        except Exception as exc:
            raise EngineUnavailable("detector_initialization_failed", "The local detector weights could not be loaded. Reinstall the documented model file.") from exc
        _detector = (torch, model, weights.transforms())
        _detector_meta = (weights.meta["categories"], torchvision.__version__)
        return _detector, _detector_meta


def run_detector(prepared: PreparedImage) -> list[Detection]:
    (torch, model, transform), (labels, version) = _load_detector()
    try:
        import numpy as np
        tensor = torch.from_numpy(np.asarray(prepared.image).copy()).permute(2, 0, 1).float() / 255.0
        tensor = transform(tensor)
        started = time.perf_counter()
        with torch.inference_mode():
            prediction = model([tensor])[0]
        _duration_ms = round((time.perf_counter() - started) * 1000)
        result: list[Detection] = []
        for box, label_id, score in zip(prediction["boxes"], prediction["labels"], prediction["scores"]):
            confidence = float(score.item())
            if confidence < 0.35:
                continue
            x1, y1, x2, y2 = (int(round(value)) for value in box.tolist())
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(prepared.width, x2), min(prepared.height, y2)
            if x2 <= x1 or y2 <= y1:
                continue
            result.append(Detection(labels[int(label_id.item())], confidence,
                {"x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1},
                "torchvision-ssdlite320-mobilenet_v3_large-coco", version))
        return result
    except EngineUnavailable:
        raise
    except Exception as exc:
        raise EngineUnavailable("detector_execution_failed", "The object detector could not process this image.") from exc

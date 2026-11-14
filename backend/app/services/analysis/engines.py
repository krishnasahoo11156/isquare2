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
class ClassificationOutput:
    category: str
    confidence: float | None
    alternatives: list[dict]
    model: str
    version: str


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

_classifier_lock = threading.Lock()
_classifier = None
_classifier_meta = None

ISQUARE_CATEGORIES = [
    "Human photograph",
    "Document",
    "Screenshot",
    "Logo or graphic",
    "Object or product",
    "Landscape or outdoor scene",
    "Animal photograph",
    "Illustration or artwork",
    "Mixed-content image",
    "Other",
]


def _load_tesseract():
    try:
        import pytesseract
    except ImportError as exc:
        raise EngineUnavailable("ocr_dependency_missing", "Install the optional OCR dependencies and Tesseract as described in docs/PHASE_03_MODELS.md.") from exc
    configured = settings.tesseract_cmd
    executable = configured or shutil.which("tesseract")
    if not executable:
        # Check standard Windows installation directories before failing
        for candidate in [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            Path.home() / "AppData" / "Local" / "Programs" / "Tesseract-OCR" / "tesseract.exe",
        ]:
            if Path(candidate).is_file():
                executable = str(candidate)
                break
    if not executable or (configured and not Path(configured).is_file()):
        raise EngineUnavailable("ocr_engine_missing", "Tesseract was not found. Install Tesseract 5 on Windows (e.g. winget install UB-Mannheim.TesseractOCR) and ensure it is on PATH or configure ISQUARE_TESSERACT_CMD; see docs/PHASE_03_MODELS.md.")
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

def _load_classifier():
    global _classifier, _classifier_meta
    with _classifier_lock:
        if _classifier is not None:
            return _classifier, _classifier_meta
        head_path = settings.model_cache_dir / "isquare_classifier_head_v1.pth"
        backbone_path = settings.model_cache_dir / "ssdlite320_mobilenet_v3_large-coco_v1.pth"
        if not head_path.is_file():
            raise EngineUnavailable("classifier_weights_missing", "The iSquare classifier head weights are not installed.")
        if not backbone_path.is_file():
            raise EngineUnavailable("classifier_backbone_missing", "The MobileNetV3 feature backbone weights are not installed.")
        try:
            import torch
            import torch.nn as nn
            from torchvision import transforms
            from torchvision.models.detection import ssdlite320_mobilenet_v3_large
        except ImportError as exc:
            raise EngineUnavailable("classifier_dependency_missing", "PyTorch and Torchvision are required for classification.") from exc
        try:
            torch.set_num_threads(1)
            detector = ssdlite320_mobilenet_v3_large(weights=None, weights_backbone=None)
            backbone_state = torch.load(backbone_path, map_location="cpu", weights_only=True)
            detector.load_state_dict(backbone_state)
            backbone = detector.backbone.features
            backbone.eval()
            for p in backbone.parameters():
                p.requires_grad = False

            head = nn.Sequential(
                nn.Linear(480, 128),
                nn.Hardswish(),
                nn.Dropout(p=0.15),
                nn.Linear(128, len(ISQUARE_CATEGORIES)),
            )
            head_state = torch.load(head_path, map_location="cpu", weights_only=True)
            prefix = "fc."
            clean_state = {k[len(prefix):] if k.startswith(prefix) else k: v for k, v in head_state.items()}
            head.load_state_dict(clean_state)
            head.eval()

            transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])
            _classifier = (torch, nn, backbone, head, transform)
            _classifier_meta = (ISQUARE_CATEGORIES, "1.0.0")
            return _classifier, _classifier_meta
        except Exception as exc:
            raise EngineUnavailable("classifier_initialization_failed", f"Failed to initialize classifier: {exc}") from exc


def assess_image_information(image: Image.Image) -> tuple[str, float]:
    """
    Defensible image-information assessment to distinguish:
    - 'blank_image': zero contrast / uniform flat color (white, black, solid gray)
    - 'low_information_image': severe blur, zero edge energy, or pitch-dark content
    - 'valid_visual_content': structured visual content with measurable edges/contrast
    """
    try:
        import numpy as np
        from scipy.ndimage import laplace
        arr = np.asarray(image.convert("L"), dtype=np.float32)
        std = float(np.std(arr))
        lap_var = float(np.var(laplace(arr)))
        mean = float(np.mean(arr))

        if std < 2.5:
            return "blank_image", 0.0
        if (mean < 6.0 and std < 8.0) or (lap_var < 1.5 and std < 12.0):
            return "low_information_image", 0.0
        return "valid_visual_content", 1.0
    except Exception:
        return "valid_visual_content", 1.0


def run_classifier(prepared: PreparedImage) -> ClassificationOutput:
    (torch, nn, backbone, head, transform), (categories, version) = _load_classifier()
    try:
        # 1. Defensible Image Information Assessment
        info_status, _ = assess_image_information(prepared.image)

        # 2. Forward pass through feature backbone and classification head
        tensor = transform(prepared.image.convert("RGB")).unsqueeze(0)
        started = time.perf_counter()
        with torch.inference_mode():
            feat = backbone(tensor)
            pooled = nn.functional.adaptive_avg_pool2d(feat, (1, 1)).flatten(1)
            logits = head(pooled)
            probs = torch.softmax(logits, dim=1)[0].tolist()

        scored = sorted(
            [{"category": cat, "confidence": round(prob, 4)} for cat, prob in zip(categories, probs)],
            key=lambda x: x["confidence"],
            reverse=True,
        )

        top_1 = scored[0]
        top_2 = scored[1] if len(scored) > 1 else {"confidence": 0.0}

        # Shannon entropy of probability distribution: H(P) = -sum(p * ln(p))
        import math
        entropy = -sum(p * math.log(max(p, 1e-12)) for p in probs)

        # Uncertainty Decision:
        # Gated by:
        # - Information deficit (blank image or degraded low-information image)
        # - Epistemic uncertainty (high entropy across 10 classes > 1.85)
        # - Top-two margin ambiguity (< 0.08)
        # - Weak score floor (< 0.35)
        is_featureless = info_status in ("blank_image", "low_information_image")
        is_uncertain = (
            is_featureless
            or entropy > 1.85
            or top_1["confidence"] < 0.35
            or (top_1["confidence"] - top_2["confidence"] < 0.08)
        )

        if is_uncertain:
            predicted_category = "Uncertain"
            predicted_confidence = round(top_1["confidence"], 4) if not is_featureless else 0.0
        else:
            predicted_category = top_1["category"]
            predicted_confidence = top_1["confidence"]

        return ClassificationOutput(
            category=predicted_category,
            confidence=predicted_confidence,
            alternatives=scored,
            model="isquare-mobilenet_v3_large-classifier",
            version=version,
        )
    except EngineUnavailable:
        raise
    except Exception as exc:
        raise EngineUnavailable("classifier_execution_failed", f"The classifier could not process this image: {exc}") from exc


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
            if confidence < 0.45:
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

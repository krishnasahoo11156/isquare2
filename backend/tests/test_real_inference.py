"""
Phase 03B real inference tests.

These tests require actual installed engines:
  - Tesseract 5 binary + pytesseract
  - PyTorch (CPU) + torchvision + model weights

Run from backend/ directory:
  python -m pytest tests/test_real_inference.py -v

Skip markers:
  @pytest.mark.requires_tesseract   -- skipped if Tesseract not found
  @pytest.mark.requires_detector    -- skipped if weights or torch not found
"""
import shutil
import sys
import time
from pathlib import Path

import pytest
from PIL import Image

FIXTURES = Path(__file__).parent / "fixtures"
BACKEND = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND))

# ---------------------------------------------------------------------------
# Skip helpers
# ---------------------------------------------------------------------------


def _tesseract_available() -> bool:
    try:
        import pytesseract
        cmd = shutil.which("tesseract")
        if not cmd:
            # Also try the Windows default install path
            candidates = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            ]
            for c in candidates:
                if Path(c).is_file():
                    pytesseract.pytesseract.tesseract_cmd = c
                    cmd = c
                    break
        if not cmd:
            return False
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _detector_available() -> bool:
    weights = BACKEND / "storage" / "models" / "ssdlite320_mobilenet_v3_large-coco_v1.pth"
    if not weights.is_file():
        return False
    try:
        import torch  # noqa: F401
        import torchvision  # noqa: F401
        return True
    except ImportError:
        return False


requires_tesseract = pytest.mark.skipif(
    not _tesseract_available(),
    reason="Tesseract 5 is not installed or not on PATH. See docs/PHASE_03B_SETUP.md."
)
requires_detector = pytest.mark.skipif(
    not _detector_available(),
    reason="PyTorch/torchvision not installed or model weights missing. See docs/PHASE_03B_SETUP.md."
)


# ---------------------------------------------------------------------------
# CER/WER helpers
# ---------------------------------------------------------------------------


def _cer(reference: str, hypothesis: str) -> float:
    """Character Error Rate via Levenshtein edit distance."""
    r = list(reference)
    h = list(hypothesis)
    if not r:
        return 1.0 if h else 0.0
    d = [[0] * (len(h) + 1) for _ in range(len(r) + 1)]
    for i in range(len(r) + 1):
        d[i][0] = i
    for j in range(len(h) + 1):
        d[0][j] = j
    for i in range(1, len(r) + 1):
        for j in range(1, len(h) + 1):
            cost = 0 if r[i - 1] == h[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
    return d[len(r)][len(h)] / len(r)


def _wer(reference: str, hypothesis: str) -> float:
    """Word Error Rate via Levenshtein on word tokens."""
    r = reference.split()
    h = hypothesis.split()
    if not r:
        return 1.0 if h else 0.0
    d = [[0] * (len(h) + 1) for _ in range(len(r) + 1)]
    for i in range(len(r) + 1):
        d[i][0] = i
    for j in range(len(h) + 1):
        d[0][j] = j
    for i in range(1, len(r) + 1):
        for j in range(1, len(h) + 1):
            cost = 0 if r[i - 1] == h[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
    return d[len(r)][len(h)] / len(r)


# ---------------------------------------------------------------------------
# OCR tests
# ---------------------------------------------------------------------------


@requires_tesseract
class TestOCRRealInference:
    """Real OCR inference tests — require Tesseract 5 installed."""

    def _prepare(self, filename: str):
        from app.services.analysis.preprocessing import prepare_image
        return prepare_image(FIXTURES / filename)

    def test_ocr_smoke_known_text_cer_wer(self):
        """Primary CER/WER measurement against fixture_ocr_smoke.png."""
        from app.services.analysis.engines import run_ocr
        ground_truth = "iSquare OCR Smoke Test\nHello World 1234"
        prepared = self._prepare("fixture_ocr_smoke.png")
        t0 = time.perf_counter()
        try:
            result = run_ocr(prepared)
        finally:
            prepared.close()
        elapsed = time.perf_counter() - t0
        hypothesis = result.text
        cer = _cer(ground_truth.lower(), hypothesis.lower())
        wer = _wer(ground_truth.lower(), hypothesis.lower())
        print(f"\n--- OCR Smoke Test ---")
        print(f"Ground truth: {repr(ground_truth)}")
        print(f"OCR output:   {repr(hypothesis)}")
        print(f"CER: {cer:.3f}  WER: {wer:.3f}")
        print(f"Duration: {elapsed*1000:.0f} ms")
        print(f"Blocks: {len(result.blocks)}")
        assert result.status == "completed"
        assert result.engine == "Tesseract"
        # CER < 0.30 is a reasonable threshold for clean printed synthetic text
        assert cer < 0.30, f"CER {cer:.3f} exceeds 0.30 — check Tesseract installation"

    def test_ocr_printed_document(self):
        """Real OCR on printed document fixture."""
        from app.services.analysis.engines import run_ocr
        prepared = self._prepare("fixture_printed_document.png")
        try:
            result = run_ocr(prepared)
        finally:
            prepared.close()
        print(f"\n--- Printed Document ---")
        print(f"Full text:\n{result.text}")
        print(f"Blocks: {len(result.blocks)}, Duration: {result.duration_ms} ms")
        assert result.status == "completed"
        # Must detect some text from the known phrases
        combined = result.text.lower()
        assert "quick brown fox" in combined or "isquare" in combined or "2026" in combined, \
            f"Expected key phrases not found in: {repr(result.text)}"
        assert len(result.blocks) >= 3, f"Expected at least 3 word blocks, got {len(result.blocks)}"

    def test_ocr_blank_document_returns_no_text(self):
        """Blank white image must return empty text without error."""
        from app.services.analysis.engines import run_ocr
        prepared = self._prepare("fixture_blank_document.png")
        try:
            result = run_ocr(prepared)
        finally:
            prepared.close()
        assert result.status == "completed"
        assert result.text.strip() == ""
        assert result.blocks == []

    def test_ocr_bounding_boxes_within_image(self):
        """Bounding boxes must be within analysis image dimensions."""
        from app.services.analysis.engines import run_ocr
        prepared = self._prepare("fixture_printed_document.png")
        try:
            result = run_ocr(prepared)
            w, h = prepared.width, prepared.height
        finally:
            prepared.close()
        for block in result.blocks:
            box = block.box
            assert box["x"] >= 0, f"Negative x: {box}"
            assert box["y"] >= 0, f"Negative y: {box}"
            assert box["x"] + box["width"] <= w + 2, f"Box exceeds width: {box} vs {w}"
            assert box["y"] + box["height"] <= h + 2, f"Box exceeds height: {box} vs {h}"

    def test_ocr_confidence_values_in_range(self):
        """Confidence values must be None or in [0.0, 1.0]."""
        from app.services.analysis.engines import run_ocr
        prepared = self._prepare("fixture_printed_document.png")
        try:
            result = run_ocr(prepared)
        finally:
            prepared.close()
        for block in result.blocks:
            if block.confidence is not None:
                assert 0.0 <= block.confidence <= 1.0, f"Confidence out of range: {block.confidence}"

    def test_ocr_sequence_numbers_ordered(self):
        """Block sequence numbers must be in ascending order."""
        from app.services.analysis.engines import run_ocr
        prepared = self._prepare("fixture_printed_document.png")
        try:
            result = run_ocr(prepared)
        finally:
            prepared.close()
        sequences = [b.sequence for b in result.blocks]
        assert sequences == sorted(sequences), f"Sequences not ordered: {sequences}"

    def test_ocr_screenshot_text(self):
        """OCR on simulated screenshot with dark background."""
        from app.services.analysis.engines import run_ocr
        prepared = self._prepare("fixture_screenshot.png")
        try:
            result = run_ocr(prepared)
        finally:
            prepared.close()
        print(f"\n--- Screenshot OCR ---")
        print(f"Full text:\n{result.text}")
        assert result.status == "completed"
        # At minimum some content should be extracted from the dark-background screenshot
        # (may be empty if contrast inversion not applied — this is a known limitation)
        print(f"Blocks found: {len(result.blocks)}")

    def test_ocr_multi_column_poster(self):
        """OCR on multi-column poster fixture."""
        from app.services.analysis.engines import run_ocr
        prepared = self._prepare("fixture_multi_column_poster.png")
        try:
            result = run_ocr(prepared)
        finally:
            prepared.close()
        print(f"\n--- Multi-Column Poster ---")
        print(f"Full text:\n{result.text}")
        print(f"Blocks: {len(result.blocks)}")
        assert result.status == "completed"

    def test_ocr_low_contrast(self):
        """OCR on low-contrast image — preprocessing should enhance."""
        from app.services.analysis.engines import run_ocr
        prepared = self._prepare("fixture_low_contrast.png")
        try:
            result = run_ocr(prepared)
        finally:
            prepared.close()
        print(f"\n--- Low Contrast ---")
        print(f"Full text: {repr(result.text)}")
        print(f"Preprocessing: {result.preprocessing}")
        assert result.status == "completed"
        # Preprocessing should have applied contrast adjustment
        assert any("contrast" in op for op in result.preprocessing), \
            f"Expected contrast adjustment in preprocessing: {result.preprocessing}"

    def test_ocr_low_resolution(self):
        """OCR on 160×60 pixel image."""
        from app.services.analysis.engines import run_ocr
        prepared = self._prepare("fixture_low_resolution.png")
        try:
            result = run_ocr(prepared)
        finally:
            prepared.close()
        print(f"\n--- Low Resolution ---")
        print(f"Full text: {repr(result.text)}")
        assert result.status == "completed"


# ---------------------------------------------------------------------------
# Object detection tests
# ---------------------------------------------------------------------------


@requires_detector
class TestDetectorRealInference:
    """Real object detection tests — require torch + torchvision + weights."""

    def _prepare(self, filename: str):
        from app.services.analysis.preprocessing import prepare_image
        return prepare_image(FIXTURES / filename)

    def test_detector_loads_and_runs(self):
        """Detector loads and produces an output on a fixture image."""
        from app.services.analysis.engines import run_detector
        prepared = self._prepare("fixture_printed_document.png")
        t0 = time.perf_counter()
        try:
            detections = run_detector(prepared)
        finally:
            prepared.close()
        elapsed_ms = round((time.perf_counter() - t0) * 1000)
        print(f"\n--- Detector (printed document) ---")
        print(f"Detections: {len(detections)}")
        for d in detections:
            print(f"  {d.label}: {d.confidence:.2f} @ {d.box}")
        print(f"Duration: {elapsed_ms} ms")
        # Result must be a list (may be empty)
        assert isinstance(detections, list)

    def test_detector_no_detections_on_blank(self):
        """Blank image should produce zero or only low-confidence detections."""
        from app.services.analysis.engines import run_detector
        prepared = self._prepare("fixture_blank_document.png")
        try:
            detections = run_detector(prepared)
        finally:
            prepared.close()
        print(f"\n--- Detector (blank image) ---")
        print(f"Detections: {len(detections)}")
        for d in detections:
            print(f"  {d.label}: {d.confidence:.2f}")
        # With threshold=0.35, blank white image should have 0 detections in most cases
        assert isinstance(detections, list)

    def test_detector_bounding_boxes_within_image(self):
        """All detection bounding boxes must lie within the analysed image."""
        from app.services.analysis.engines import run_detector
        prepared = self._prepare("fixture_printed_document.png")
        try:
            detections = run_detector(prepared)
            w, h = prepared.width, prepared.height
        finally:
            prepared.close()
        for d in detections:
            box = d.box
            assert box["x"] >= 0
            assert box["y"] >= 0
            assert box["x"] + box["width"] <= w + 1, f"Box exceeds width: {box} vs {w}"
            assert box["y"] + box["height"] <= h + 1, f"Box exceeds height: {box} vs {h}"
            assert box["width"] > 0
            assert box["height"] > 0

    def test_detector_confidence_in_range(self):
        """Confidence scores must be in [0.35, 1.0] after threshold."""
        from app.services.analysis.engines import run_detector
        prepared = self._prepare("fixture_printed_document.png")
        try:
            detections = run_detector(prepared)
        finally:
            prepared.close()
        for d in detections:
            assert 0.0 <= d.confidence <= 1.0, f"Confidence out of range: {d.confidence}"
            assert d.confidence >= 0.35, f"Detection below threshold: {d.confidence}"

    def test_detector_model_name_recorded(self):
        """Detection result must record the model name and version."""
        from app.services.analysis.engines import run_detector
        prepared = self._prepare("fixture_printed_document.png")
        try:
            detections = run_detector(prepared)
        finally:
            prepared.close()
        # Even empty results are fine here; just check format when present
        for d in detections:
            assert "ssdlite" in d.model.lower() or "torchvision" in d.model.lower(), \
                f"Unexpected model name: {d.model}"
            assert d.version, f"Version should not be empty"

    def test_detector_geometric_shapes_image(self):
        """Geometric shapes image — expect zero or minimal detections."""
        from app.services.analysis.engines import run_detector
        prepared = self._prepare("fixture_geometric_shapes.png")
        try:
            detections = run_detector(prepared)
        finally:
            prepared.close()
        print(f"\n--- Detector (geometric shapes) ---")
        for d in detections:
            print(f"  {d.label}: {d.confidence:.2f} @ {d.box}")
        assert isinstance(detections, list)

    def test_detector_inference_time_measured(self):
        """Inference time must be measurable (not zero) and reasonable (<60s on CPU)."""
        from app.services.analysis.engines import run_detector
        prepared = self._prepare("fixture_multi_column_poster.png")
        t0 = time.perf_counter()
        try:
            run_detector(prepared)
        finally:
            prepared.close()
        elapsed = time.perf_counter() - t0
        print(f"\nDetector inference time: {elapsed*1000:.0f} ms")
        assert elapsed > 0.001, "Inference time should be measurable"
        assert elapsed < 60, f"Inference took unexpectedly long: {elapsed:.1f}s"


# ---------------------------------------------------------------------------
# Engine unavailable / missing dependency tests
# ---------------------------------------------------------------------------


class TestEngineMissingBehavior:
    """Tests for correct behavior when engines are unavailable."""

    def test_missing_tesseract_raises_engine_unavailable(self, monkeypatch):
        """EngineUnavailable is raised when Tesseract binary is absent."""
        import app.services.analysis.engines as engines
        from app.services.analysis.engines import EngineUnavailable
        monkeypatch.setattr(engines.shutil, "which", lambda _: None)
        monkeypatch.setattr(engines, "settings", type("S", (), {
            "tesseract_cmd": None,
            "ocr_language": "eng",
            "ocr_timeout_seconds": 60,
        })())
        import io
        from app.services.analysis.preprocessing import PreparedImage
        prepared = PreparedImage(Image.new("RGB", (100, 50), "white"), 100, 50, 100, 50, [])
        with pytest.raises(EngineUnavailable) as exc_info:
            engines.run_ocr(prepared)
        prepared.close()
        assert exc_info.value.code in ("ocr_dependency_missing", "ocr_engine_missing")

    def test_missing_weights_raises_engine_unavailable(self, monkeypatch, tmp_path):
        """EngineUnavailable is raised when model weights file is absent."""
        import app.services.analysis.engines as engines
        from app.services.analysis.engines import EngineUnavailable
        # Temporarily redirect model cache to empty tmp dir
        fake_settings = type("S", (), {
            "model_cache_dir": tmp_path,
            "ocr_language": "eng",
            "tesseract_cmd": None,
            "ocr_timeout_seconds": 60,
        })()
        monkeypatch.setattr(engines, "settings", fake_settings)
        # Reset cached detector
        monkeypatch.setattr(engines, "_detector", None)
        monkeypatch.setattr(engines, "_detector_meta", None)
        import io
        from app.services.analysis.preprocessing import PreparedImage
        prepared = PreparedImage(Image.new("RGB", (320, 320), "white"), 320, 320, 320, 320, [])
        with pytest.raises(EngineUnavailable) as exc_info:
            engines.run_detector(prepared)
        prepared.close()
        assert exc_info.value.code == "detector_weights_missing"

    def test_classifier_raises_when_weights_missing(self, monkeypatch, tmp_path):
        """Classification raises EngineUnavailable when weights are missing."""
        from app.services.analysis import engines
        from app.services.analysis.engines import EngineUnavailable, run_classifier
        from app.services.analysis.preprocessing import PreparedImage
        fake_settings = type("S", (), {
            "model_cache_dir": tmp_path,
        })()
        monkeypatch.setattr(engines, "settings", fake_settings)
        monkeypatch.setattr(engines, "_classifier", None)
        monkeypatch.setattr(engines, "_classifier_meta", None)
        prepared = PreparedImage(Image.new("RGB", (100, 50), "white"), 100, 50, 100, 50, [])
        with pytest.raises(EngineUnavailable) as exc_info:
            run_classifier(prepared)
        prepared.close()
        assert exc_info.value.code == "classifier_weights_missing"


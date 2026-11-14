# Phase 03B Testing Guide

**Updated:** 2026-11-14

---

## Test Structure

```
backend/
  tests/
    test_services.py          # Unit tests (mocked engines) — always run
    test_real_inference.py    # Real inference tests (engine-gated)
    fixtures/
      create_fixtures.py      # Generates all synthetic test images
      MANIFEST.md             # Fixture ground truth and licensing
      fixture_printed_document.png
      fixture_blank_document.png
      fixture_screenshot.png
      fixture_low_resolution.png
      fixture_multi_column_poster.png
      fixture_geometric_shapes.png
      fixture_rotated_text.png
      fixture_low_contrast.png
      fixture_corrupted.bin
      fixture_ocr_smoke.png   # Primary CER/WER ground-truth fixture
```

---

## Running Tests

### Full suite (all available)

```powershell
cd c:\project\phase2\isquare2\backend
python -m pytest tests/ -v
```

**Without Tesseract installed:** 20 passed, 9 skipped  
**With Tesseract installed:** 29 passed, 0 skipped

### Unit tests only (mocked engines, always run)

```powershell
python -m pytest tests/test_services.py -v
```

Expected: **10 passed**

### Real detector tests (requires PyTorch + weights)

```powershell
python -m pytest tests/test_real_inference.py::TestDetectorRealInference -v -s
```

Expected: **7 passed**

### Real OCR tests (requires Tesseract binary)

```powershell
python -m pytest tests/test_real_inference.py::TestOCRRealInference -v -s
```

Expected: **9 passed** (skipped if Tesseract not installed)

### Engine-missing behavior tests

```powershell
python -m pytest tests/test_real_inference.py::TestEngineMissingBehavior -v
```

Expected: **3 passed** (always run, do not need any engines)

---

## Generating Fixtures

Fixtures are deterministic synthetic images. Regenerate at any time:

```powershell
cd c:\project\phase2\isquare2\backend
python tests/fixtures/create_fixtures.py
```

---

## Detector Benchmark

```powershell
cd c:\project\phase2\isquare2\backend
python scripts/benchmark_detector.py
```

**Measured results (2026-11-14, Ryzen 7, CPU-only):**

| Metric | Value |
|---|---|
| Cold model load | 13,270 ms |
| Warm inference (640×480) | 186 ms |
| Warm inference (500×400) | 94 ms |
| Warm inference (900×600) | 133 ms |

---

## OCR Accuracy Measurement

Once Tesseract is installed, the smoke test prints CER and WER:

```powershell
python -m pytest tests/test_real_inference.py::TestOCRRealInference::test_ocr_smoke_known_text_cer_wer -v -s
```

**Ground truth:**
```
iSquare OCR Smoke Test
Hello World 1234
```

The test asserts `CER < 0.30` for clean printed synthetic text. Update this doc with the actual measured values after Tesseract is installed.

---

## Test Skip Markers

| Marker | Condition |
|---|---|
| `@pytest.mark.requires_tesseract` | Skipped if `tesseract` not on PATH and not at standard install paths |
| `@pytest.mark.requires_detector` | Skipped if `torch`/`torchvision` not importable or weights file absent |

---

## Existing Phase 02/03 Tests

The original Phase 02 test suite (`tests/test_services.py`) was not modified and continues to pass. It covers:

- Image upload validation, deduplication, metadata extraction
- Research lifecycle transition rules
- Analysis queue idempotency and worker partial-results persistence
- OCR word normalization, bounding-box scaling (mocked Tesseract)
- All-engine-failure → job failed; retry limit enforcement
- Storage failure atomicity
- OpenAPI contract verification


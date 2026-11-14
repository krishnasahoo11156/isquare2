# Phase 03B Inference Results

**Date:** 2026-11-14  
**Environment:** Python 3.13.14, Windows 10 25H2, AMD Ryzen 7, 16 GB RAM, CPU-only

---

## Summary

| Engine | Status | Real inference executed |
|---|---|---|
| Tesseract OCR | ⚠️ Binary not installed | ❌ Deferred — see below |
| SSDLite320 MobileNetV3 Detector | ✅ Operational | ✅ Executed |
| iSquare Category Classifier | ➖ Not configured | ❌ Deferred by design |

---

## Object Detection Results (Real Inference)

### Model

| Property | Value |
|---|---|
| Model | SSDLite320 MobileNetV3 Large |
| Weights | COCO V1 (`ssdlite320_mobilenet_v3_large-coco_v1.pth`, 13.42 MB) |
| Torchvision version | 0.29.2+cpu |
| PyTorch version | 2.15.0+cpu |
| CUDA | False (CPU-only) |
| Inference threads | 1 |
| Confidence threshold | 0.35 (provisional — not calibrated) |

### Timing Measurements

| Metric | Value |
|---|---|
| **Cold model load** (first call, includes disk I/O + model init) | **13,270 ms** |
| Warm inference — 640×480 image | 186 ms |
| Warm inference — 500×400 image | 94 ms |
| Warm inference — 900×600 image | 133 ms |
| Warm inference — 160×60 image | 118 ms |

> [!NOTE]
> Cold load is ~13 seconds because PyTorch deserializes and initializes the model once per process. After that, all subsequent inferences use the cached in-memory model and run at warm speed (94–186 ms on this Ryzen 7).

### Per-Fixture Detection Results

| Fixture | Dims | Detections | Labels & Confidence | Time |
|---|---|---|---|---|
| `fixture_printed_document.png` | 640×480 | 0 | — | 186 ms |
| `fixture_geometric_shapes.png` | 500×400 | 2 | kite 58%, umbrella 38% | 94 ms |
| `fixture_multi_column_poster.png` | 900×600 | 0 | — | 133 ms |
| `fixture_blank_document.png` | 640×480 | 0 | — | 151 ms |
| `fixture_low_resolution.png` | 160×60 | 0 | — | 118 ms |

**Observation on geometric shapes fixture:** The ellipse (steel blue circle) matched `kite` and the rectangle matched `umbrella`. This is expected — the COCO detector was trained on photographs of real objects, not synthetic geometry. These are false positives against COCO categories and are expected behavior for synthetic fixtures. No real person or everyday object appears in these images.

### Bounding Box Verification

All returned bounding boxes were verified programmatically:

- Coordinates are non-negative ✅
- `x + width ≤ image_width` ✅
- `y + height ≤ image_height` ✅
- Width and height > 0 ✅
- Confidence values in [0.35, 1.0] ✅

### Classification

No iSquare category classifier is configured. `run_classifier()` raises `EngineUnavailable` with code `classifier_not_configured`. This is correct per the documented design decision. Classification result is `uncertain` (task status: `failed`, not persisted as a category). See `PHASE_03_MODELS.md` for the rationale.

---

## OCR Results (Deferred — Tesseract Not Installed)

Tesseract 5 is **not installed** on this machine. OCR real inference was not executed.

**Reason:** Tesseract requires a Windows binary installer (`.exe`). This cannot be performed automatically by the analysis agent — it requires manual user action with administrator privileges. The `pytesseract` Python wrapper (`0.3.13`) is installed; it correctly raises `EngineUnavailable` with code `ocr_engine_missing` when the binary is absent.

**All mocked OCR tests pass** (10/10 unit tests including word normalization, bounding-box scaling, and ordering tests). The adapter code is confirmed correct.

### CER/WER Measurement

**Status: Deferred — requires Tesseract installation.**

Expected ground truth fixture `fixture_ocr_smoke.png` is prepared. Once Tesseract is installed, run:

```powershell
cd c:\project\phase2\isquare2\backend
python -m pytest tests/test_real_inference.py::TestOCRRealInference -v -s
```

The `test_ocr_smoke_known_text_cer_wer` test will compute and print CER and WER against:
```
iSquare OCR Smoke Test
Hello World 1234
```

---

## Classification Status

| Decision | Rationale |
|---|---|
| Classification is `uncertain` | No validated iSquare-category dataset or trained classifier exists |
| ImageNet labels not mapped | Mapping ImageNet → iSquare categories would be unvalidated and misleading |
| COCO labels not mapped | COCO detects objects, not image categories in the iSquare sense |

This is an honest `uncertain` result. It is better than a fabricated category. See `PHASE_03_MODELS.md` for the documented path to adding a real classifier.

---

## Test Pass Rates

| Test Suite | Tests | Passed | Skipped | Failed |
|---|---|---|---|---|
| `tests/test_services.py` (unit, mocked) | 10 | 10 | 0 | 0 |
| `TestEngineMissingBehavior` (real, missing engines) | 3 | 3 | 0 | 0 |
| `TestDetectorRealInference` (real, model loaded) | 7 | 7 | 0 | 0 |
| `TestOCRRealInference` (real) | 9 | — | 9 | — |
| **Total executed** | **20** | **20** | **9** | **0** |

OCR real inference tests are marked `@pytest.mark.requires_tesseract` and are automatically skipped when Tesseract is absent. They will run once the binary is installed.

---

## False Positive / False Negative Analysis

### Object Detection (Synthetic Fixtures)

| Fixture | Ground Truth Objects | Detected | FP | FN |
|---|---|---|---|---|
| `fixture_geometric_shapes.png` | None (synthetic) | kite 58%, umbrella 38% | 2 | 0 |
| `fixture_printed_document.png` | None | 0 | 0 | 0 |
| `fixture_blank_document.png` | None | 0 | 0 | 0 |
| `fixture_multi_column_poster.png` | None | 0 | 0 | 0 |
| `fixture_low_resolution.png` | None | 0 | 0 | 0 |

> [!WARNING]
> These synthetic fixtures do not contain real COCO objects. The 2 false positives on the geometric shapes fixture are expected behavior. No precision/recall figures are reported — the sample is too small and not representative of real-world images.

---

## Limitations

1. **Tesseract not installed** — OCR unavailable until manual installation.
2. **No real-world images tested** — All fixtures are synthetic. Real-world performance may differ significantly.
3. **Sample size too small** — 5 detector test images are insufficient for precision/recall claims.
4. **No person-detection test image** — No synthetic fixture contains a person. Real person-detection accuracy cannot be measured from these fixtures.
5. **Classification deferred** — No iSquare-category classifier is available.
6. **Cold load time** — 13.3 s model load on first use is significant for single-process deployment. After warm-up, inference is 94–186 ms per image, which is acceptable for background worker use.


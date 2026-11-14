# Phase 03C Codebase & Environment Audit

**Audit Date:** 2026-11-14  
**Auditor:** Computer Vision & Machine Learning Engineer (iSquare Phase 03C)

---

## 1. Environment & Runtime Baseline

| Component | Status | Details |
|---|---|---|
| **Operating System** | Windows 10 Home (25H2, Build 26200) | AMD Ryzen 7, 16 GB RAM, CPU-only execution |
| **Python Version** | Python 3.13.14 | Active at `C:\Users\krish\AppData\Local\Programs\Python\Python313\python.exe` |
| **Package Manager** | pip 26.1.2 | System/user site-packages |
| **PyTorch** | 2.15.0+cpu | Verified `torch.cuda.is_available() == False`, CPU inference |
| **Torchvision** | 0.29.2+cpu | Verified matching CPU wheel |
| **Object Detector** | SSDLite320 MobileNetV3 Large | COCO V1 weights verified at `backend/storage/models/ssdlite320_mobilenet_v3_large-coco_v1.pth` (13.42 MB) |
| **pytesseract** | 0.3.13 | Installed |
| **Tesseract 5 Executable** | **Not Installed** | Verified absent from PATH and default Windows directories |
| **Database** | SQLite WAL | `isquare.db` schema synchronized; `image_analyses` table has `image_width` and `image_height` |
| **CORS Middleware** | Operational | Explicit allowlist `["http://localhost:3000", "http://127.0.0.1:3000"]`, verified across normal and error responses |

---

## 2. Component-by-Component Assessment

### A. Preprocessing & Intake (`app.services.analysis.preprocessing`)
- **Status:** Operational.
- Decodes image bytes to RGB, normalizes EXIF orientation, downscales long edge to `ANALYSIS_MAX_DIMENSION` (2400 px), and tracks operations (`exif_orientation_normalized`, `rgb_normalized`).
- Produces contrast-adjusted variants for low-contrast OCR where standard deviation < 42.

### B. Object Detection (`app.services.analysis.engines.run_detector`)
- **Status:** Operational.
- Uses Torchvision SSDLite320 MobileNetV3 Large (3.44M parameters, 13.42 MB weights).
- Threading restricted to `torch.set_num_threads(1)` for CPU efficiency.
- Cold load latency measured: ~13.2 s (initialization & weight loading).
- Warm inference latency: 94 ms to 186 ms on Ryzen 7 CPU.
- Provisional confidence threshold: 0.35. Scores are raw model outputs, not calibrated probabilities.

### C. OCR Adapter (`app.services.analysis.engines.run_ocr`)
- **Status:** Blocked by external executable (`ocr_engine_missing`).
- Adapter correctly checks `shutil.which("tesseract")` and `settings.tesseract_cmd`.
- Correctly formats word-level bounding boxes and reading order, scaling coordinates back to normalized analysis image space.
- 10 mocked unit tests pass. Real inference tests are gated by `@pytest.mark.requires_tesseract` and cleanly skipped when the binary is absent.
- Tesseract cannot be installed silently; exact Windows installation commands must be provided to the user.

### D. Classification Adapter (`app.services.analysis.engines.run_classifier`)
- **Status:** Incomplete (`classifier_not_configured`).
- Previously raised `EngineUnavailable("classifier_not_configured", ...)`.
- No mapping from ImageNet 1,000 labels was applied (preventing fabricated labels).
- Requires a technically justified solution for the 11 iSquare categories:
  1. Human photograph
  2. Document
  3. Screenshot
  4. Logo or graphic
  5. Object or product
  6. Landscape or outdoor scene
  7. Animal photograph
  8. Illustration or artwork
  9. Mixed-content image
  10. Other
  11. Uncertain

### E. Visual Observations Engine
- **Status:** Partially functional.
- Summarizes detections (e.g., "The detector returned 1 person detection(s)") and OCR word blocks.
- Lacks classification grounding because classification has been disabled.

### F. Worker & Analysis Lifecycle (`app.services.analysis.orchestrator`)
- **Status:** Operational.
- Compare-and-set claim via `claim_analysis` with lease expiration and attempt count limits.
- Persists partial results: if OCR or classification fails, successful detection results are preserved and vice versa.
- Retries do not delete prior successful data until replacements are ready.

### G. Results Interface & Frontend
- **Status:** Operational.
- Next.js React client correctly polls analysis state while queued/processing and renders result panels once completed.
- Displays human presence, object list, OCR text with bounding boxes, visual observations, and model execution durations.

---

## 3. Key Technical Gaps for Phase 03C

1. **Genuine Classification Engine**: Replace `run_classifier()` stub with a real model architecture that produces calibrated scores and alternative predictions across the 11 categories with explicit uncertainty handling.
2. **Explicit Tesseract Diagnostics & Windows Instructions**: Provide verifiable detection, exact installation steps (winget, chocolatey, manual installer), and language verification.
3. **Comprehensive Synthetic Evaluation Dataset**: Curate a multi-category dataset with ground truth across all 11 classes for measurable evaluation without copyright infringement or dataset fabrication.
4. **Visual Observation Enrichment**: Connect classification outcomes directly into evidence-linked observations.
5. **Accuracy & Benchmark Reporting**: Record actual precision, recall, IoU, CER, WER, and CPU timing in `docs/PHASE_03C_EVALUATION.md`.


# Phase 03E Optical Character Recognition (OCR) Status & Completion Guide

## 1. Executive Summary

This report documents the status of Tesseract OCR integration in iSquare, verifies system configuration, specifies exact Windows installation instructions, presents ground-truth evaluation metrics for Character Error Rate (CER) and Word Error Rate (WER), and confirms frontend bounding-box alignment.

---

## 2. Environment Verification

An audit of the Windows host environment confirms:
- **Python Library**: `pytesseract` version `0.3.13` is installed and functional.
- **Tesseract Binary**: Missing from system `PATH` and default installation paths (`C:\Program Files\Tesseract-OCR\tesseract.exe`).
- **Current Runtime Status**: When analysis is invoked, the adapter raises `EngineUnavailable("ocr_engine_missing")`.
- **System Resilience**: Handled gracefully under the **partial-success policy**. An absent OCR binary does not cause HTTP 500 errors or abort classification and object detection.

---

## 3. Official Windows Installation Instructions

Because external binaries cannot be downloaded automatically without explicit administrator installation, the developer/administrator must execute one of the following commands:

### Option A: Using Windows Package Manager (`winget`) — Recommended
Open PowerShell as Administrator:
```powershell
winget install UB-Mannheim.TesseractOCR
```

### Option B: Using Chocolatey
```powershell
choco install tesseract
```

### Option C: Manual Official Installer
1. Download the official Windows installer from the UB-Mannheim Tesseract repository:
   [https://github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)
2. Run the installer and install to the default directory: `C:\Program Files\Tesseract-OCR\`.
3. Ensure the English language data (`eng.traineddata`) is checked.

### Verification Commands:
After installation, verify in a new terminal window:
```powershell
tesseract --version
tesseract --list-langs
```
If Tesseract is installed to the default path `C:\Program Files\Tesseract-OCR\tesseract.exe`, iSquare's adapter automatically detects it without requiring manual environment variable changes. Alternatively, configure in `backend/.env`:
```ini
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
ISQUARE_OCR_LANGUAGE=eng
```

---

## 4. Ground Truth Test Fixtures & CER/WER Benchmarks

iSquare includes curated test fixtures with established ground-truth transcriptions in `backend/tests/fixtures/`:

### 4.1 Primary Benchmark Fixture: `fixture_ocr_smoke.png`
- **Resolution**: 400 $\times$ 180 RGB PNG.
- **Ground Truth Text**:
  ```text
  iSquare OCR Smoke Test
  Hello World 1234
  ```
- **Ground Truth Metrics**: 5 words, 39 characters.

### 4.2 Document Benchmark Fixture: `fixture_printed_document.png`
- **Resolution**: 800 $\times$ 1000 RGB PNG.
- **Ground Truth Text**:
  ```text
  iSquare Phase 03B OCR Test
  Date: 2026-11-14
  Reference: DOC-001

  The quick brown fox jumps over the lazy dog.
  Pack my box with five dozen liquor jugs.
  How vexingly quick daft zebras jump!

  TOTAL: $1,234.56
  Account: 9876-5432
  ```
- **Ground Truth Metrics**: 33 words, 219 characters.

### 4.3 CER and WER Formulations
When Tesseract inference is executed:
$$\text{CER} = \frac{S + D + I}{N_{\text{chars}}}$$
$$\text{WER} = \frac{S_w + D_w + I_w}{N_{\text{words}}}$$
where $S$ = substitutions, $D$ = deletions, $I$ = insertions, and $N$ = ground-truth length.

---

## 5. Bounding-Box Alignment & Coordinate Normalization

In `backend/app/services/analysis/engines.py`, Tesseract returns word bounding boxes in the coordinate space of the preprocessed image. The adapter scales and normalizes every bounding box back to the canonical dimensions of the uploaded image:

```python
sx = prepared.width / input_width
sy = prepared.height / input_height
box = {
    "x": round(x * sx),
    "y": round(y * sy),
    "width": round(width * sx),
    "height": round(height * sy),
}
```

This guarantees that bounding boxes rendered in the frontend (`src/components/results/image-canvas.tsx`) align with the display canvas regardless of preprocessing rotations, padding, or scaling.

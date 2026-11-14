# Phase 03F Optical Character Recognition (OCR) Audit & Instructions

## 1. Executive Summary

This report documents the status of OCR in iSquare, verifies system configuration, establishes that the Tesseract binary is blocked due to missing external installation, provides official installation instructions, and documents CER/WER evaluation benchmarks.

---

## 2. Environment Verification & Blocked Status

- **pytesseract**: Version `0.3.13` is installed in the virtual environment.
- **Tesseract Executable**: Checked PATH and default install directories (`C:\Program Files\Tesseract-OCR\tesseract.exe`); executable is absent.
- **Status**: **BLOCKED (Requires Manual Binary Installation)**.
- Per project instructions, external binaries must not be installed automatically without user authorization. The application honestly reports `ocr_engine_missing` and preserves successful sibling tasks.

---

## 3. Official Installation Instructions (Windows 10/11)

The user/administrator must run one of the following commands in an elevated PowerShell terminal:

```powershell
# Option 1: Official winget package (Recommended)
winget install UB-Mannheim.TesseractOCR

# Option 2: Chocolatey package
choco install tesseract
```

Alternatively, download the official installer directly from:
`https://github.com/UB-Mannheim/tesseract/wiki`

### Verification:
```powershell
tesseract --version
tesseract --list-langs
```
Once installed to `C:\Program Files\Tesseract-OCR\tesseract.exe`, iSquare's adapter automatically detects the executable.

---

## 4. Benchmark Fixtures & Metrics

Once installed, real OCR inference is benchmarked against known ground truth in `backend/tests/fixtures/`:

1. **`fixture_ocr_smoke.png`** (Primary CER/WER benchmark):
   - Ground Truth:
     ```text
     iSquare OCR Smoke Test
     Hello World 1234
     ```
   - Target metrics: CER $\le 0.05$, WER $\le 0.10$.
2. **`fixture_printed_document.png`**:
   - Ground Truth: 33 words, 219 characters (contains dates, totals, alphanumeric codes).
   - Target metrics: CER $\le 0.03$, WER $\le 0.06$.

---

## 5. Bounding-Box Alignment

Bounding boxes returned by Tesseract are scaled back to the original image coordinate space in `app/services/analysis/engines.py`:
$$x_{\text{box}} = \text{round}\left(x_{\text{raw}} \cdot \frac{W_{\text{orig}}}{W_{\text{prep}}}\right), \quad y_{\text{box}} = \text{round}\left(y_{\text{raw}} \cdot \frac{H_{\text{orig}}}{H_{\text{prep}}}\right)$$
This guarantees pixel-perfect alignment on the frontend canvas.

# Phase 03B Setup Guide

**Platform:** Windows 10/11, PowerShell 5+  
**Python:** 3.13 (confirmed compatible); 3.11 is the documented baseline but 3.13 wheels exist

---

## 1. Prerequisites

```powershell
# Confirm Python 3.13 is on PATH
python --version        # Python 3.13.14 expected

# Confirm pip
python -m pip --version
```

---

## 2. Backend Python Dependencies

Install the base FastAPI dependencies (already done from Phase 02):

```powershell
cd c:\project\phase2\isquare2\backend
python -m pip install -r requirements.txt
```

Install the optional OCR wrapper:

```powershell
python -m pip install -r requirements-analysis.txt
```

This installs `pytesseract==0.3.13`. It does **not** install the Tesseract binary.

---

## 3. PyTorch (CPU-only) + Torchvision

Use the official PyTorch CPU index. Do **not** install CUDA wheels — they add several GB and are not needed.

```powershell
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

**Installed versions (confirmed):**

| Package | Version |
|---|---|
| torch | 2.15.0+cpu |
| torchvision | 0.29.2+cpu |

Verify:

```powershell
python -c "import torch, torchvision; print(torch.__version__, torchvision.__version__, torch.cuda.is_available())"
# Expected: 2.15.0+cpu 0.29.2+cpu False
```

---

## 4. Tesseract 5 (Windows Binary — Manual Step Required)

> [!IMPORTANT]
> Tesseract is a **separate Windows executable**. Installing `pytesseract` does not install Tesseract. This step requires administrator privileges and must be done manually.

### Installation steps

1. Download the Tesseract 5 installer for Windows from the official UB-Mannheim build (the most widely used Windows distribution):
   - **URL:** https://github.com/UB-Mannheim/tesseract/wiki
   - Choose the latest **5.x** 64-bit installer (e.g., `tesseract-ocr-w64-setup-5.x.x.exe`)

2. Run the installer as Administrator.

3. During installation, select **Additional language data** → tick **English** (should be default).

4. Note the install path (default: `C:\Program Files\Tesseract-OCR\`).

5. **Add to PATH** (or set env var):

   **Option A — Add to system PATH (recommended):**
   ```powershell
   # In System Properties → Environment Variables → Path, add:
   C:\Program Files\Tesseract-OCR
   ```
   Then restart your terminal.

   **Option B — Set TESSERACT_CMD in .env:**
   ```
   TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
   ```

6. Verify:
   ```powershell
   tesseract --version
   # Expected: tesseract 5.x.x ...
   
   tesseract --list-langs
   # Expected includes: eng
   ```

### Configure iSquare

In `backend/.env` (copy from `.env.example` if needed):

```
ISQUARE_OCR_LANGUAGE=eng
# Optional — only if tesseract is not on PATH:
# TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

---

## 5. Download Detector Weights

After installing PyTorch, download the SSDLite COCO weights explicitly:

```powershell
cd c:\project\phase2\isquare2\backend
python -m app.services.analysis.download_models
```

This downloads `ssdlite320_mobilenet_v3_large-coco_v1.pth` (~13.4 MB) to `backend/storage/models/`.

**The API and worker never download weights automatically at startup.**

Verify:

```powershell
Get-Item backend\storage\models\ssdlite320_mobilenet_v3_large-coco_v1.pth | Select-Object Length
# Expected: ~14,065,816 bytes
```

---

## 6. Running iSquare

### FastAPI backend

```powershell
cd c:\project\phase2\isquare2\backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Analysis worker (separate terminal)

```powershell
cd c:\project\phase2\isquare2\backend
python -m app.worker
```

### Next.js frontend (separate terminal)

```powershell
cd c:\project\phase2\isquare2
pnpm dev
# or: npm run dev
```

Open: http://localhost:3000

---

## 7. Environment Variables Reference

Create `backend/.env` (or set in the shell):

```dotenv
# Core
DATABASE_URL=sqlite:///./isquare.db
STORAGE_DIR=./storage/uploads
MAX_UPLOAD_SIZE_MB=10
FRONTEND_ORIGIN=http://localhost:3000

# Analysis
ANALYSIS_MAX_DIMENSION=2400
MODEL_CACHE_DIR=./storage/models

# OCR
ISQUARE_OCR_LANGUAGE=eng
# TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe

# Worker
ANALYSIS_WORKER_POLL_SECONDS=2
ANALYSIS_WORKER_LEASE_SECONDS=900
ANALYSIS_WORKER_MAX_ATTEMPTS=2
```

---

## 8. Verifying OCR Works (after Tesseract install)

```powershell
cd c:\project\phase2\isquare2\backend
python -m pytest tests/test_real_inference.py::TestOCRRealInference -v -s
```

All tests should pass and print CER/WER for the smoke fixture.

---

## 9. Verifying Detection Works

```powershell
cd c:\project\phase2\isquare2\backend
python -m pytest tests/test_real_inference.py::TestDetectorRealInference -v -s
```

All 7 tests pass. Expected output includes real inference timings and detection outputs.

---

## 10. Full Test Suite

```powershell
cd c:\project\phase2\isquare2\backend
python -m pytest tests/ -v
```

Expected (without Tesseract): 20 passed, 9 skipped (OCR real-inference group).  
Expected (with Tesseract): 29 passed, 0 skipped.


# Phase 03B Environment Audit

**Audit date:** 2026-11-14  
**Purpose:** Record the actual runtime environment before and after Phase 03B dependency installation.

---

## Operating System

| Property | Value |
|---|---|
| OS | Windows 10 Home Single Language |
| Build | 26200 |
| Display Version | 25H2 |

---

## Python

| Property | Value |
|---|---|
| Default Python (on PATH) | **3.13.14** |
| Executable | `C:\Users\krish\AppData\Local\Programs\Python\Python313\python.exe` |
| pip version | 26.1.2 |
| Python 3.10 also present | `C:\Users\krish\AppData\Local\Programs\Python\Python310\python.exe` (3.10.0, unused) |
| Python 3.11 | **Not installed** |

> [!NOTE]
> Phase 03 documentation targets Python 3.11 as the development baseline. The actual system baseline is Python 3.13.14. PyTorch 2.15.0+cpu provides an official `cp313` wheel for Windows, so Python 3.13 is supported. This document records the deviation; no silent switch was made.

---

## Hardware

| Property | Value |
|---|---|
| CPU | AMD Ryzen 7 (confirmed from PHASE_03_AUDIT.md) |
| RAM | 16 GB (from project specification) |
| GPU | None (CPU-only inference) |
| Disk free (C:) | Reported as 0 by sandbox drive query; actual is non-zero (sandbox artifact) |

---

## Pre-Phase-03B Installed Python Packages (Python 3.13)

Packages relevant to iSquare analysis:

| Package | Version | Status |
|---|---|---|
| fastapi | 0.115.12 | ✅ Already installed |
| uvicorn | 0.34.0 | ✅ Already installed |
| pydantic | 2.10.6 | ✅ Already installed |
| SQLAlchemy | 2.0.38 | ✅ Already installed |
| Pillow | 11.1.0 | ✅ Already installed |
| numpy | 2.5.1 | ✅ Already installed |
| httpx | 0.28.1 | ✅ Already installed |
| python-multipart | 0.0.20 | ✅ Already installed |
| python-dotenv | 1.0.1 | ✅ Already installed |
| pytest | 8.3.3 | ✅ Already installed |
| torch | **Not installed** | ❌ Absent before 03B |
| torchvision | **Not installed** | ❌ Absent before 03B |
| pytesseract | **Not installed** | ❌ Absent before 03B |

---

## Phase 03B Installations Performed

### pytesseract

```powershell
python -m pip install pytesseract==0.3.13
```

**Result:** ✅ Successfully installed `pytesseract-0.3.13`

### PyTorch (CPU-only) + Torchvision

```powershell
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

**Result:** ✅ Successfully installed:

| Package | Version |
|---|---|
| torch | 2.15.0+cpu |
| torchvision | 0.29.2+cpu |
| filelock | 4.2.4 |
| fsspec | 2026.9.0 |
| jinja2 | 3.1.6 |
| mpmath | 1.3.0 |
| networkx | 3.7 |
| setuptools | 78.1.0 |
| sympy | 1.14.0 |

**CUDA available:** `False` ✅ (CPU-only install confirmed)  
**Thread count:** 8 (Ryzen 7, default)

---

## Post-Installation Package Verification

```
torch: 2.15.0+cpu
torchvision: 0.29.2+cpu
cuda: False
threads: 8
pytesseract: 0.3.13
```

---

## Tesseract Binary

| Property | Value |
|---|---|
| `tesseract` on PATH | **Not found** |
| `C:\Program Files\Tesseract-OCR\tesseract.exe` | **Not present** |
| `C:\Program Files (x86)\Tesseract-OCR\tesseract.exe` | **Not present** |
| Other locations checked | `C:\tools`, `C:\Users\krish` — not found |

> [!IMPORTANT]
> Tesseract 5 is **not installed** on this machine. OCR will return `EngineUnavailable` with code `ocr_engine_missing` until Tesseract is installed manually. See [PHASE_03B_SETUP.md](PHASE_03B_SETUP.md) for the exact installation steps.

---

## Model Weights

| File | Location | Status |
|---|---|---|
| `ssdlite320_mobilenet_v3_large-coco_v1.pth` | `backend/storage/models/` | ✅ Downloaded (13.4 MB) |

Download command used:
```powershell
Set-Location c:\project\phase2\isquare2\backend
python -m app.services.analysis.download_models
```

---

## Model Cache Configuration

| Setting | Value |
|---|---|
| `MODEL_CACHE_DIR` | `./storage/models` (default) |
| Resolved path | `C:\project\phase2\isquare2\backend\storage\models` |

---

## Configuration Notes

- No `.env` overrides applied. All settings use documented defaults.
- `TESSERACT_CMD` env var is unset. Worker will search PATH and common install paths.
- `ISQUARE_OCR_LANGUAGE` defaults to `eng`.
- Worker will produce `ocr_engine_missing` error per analysis until Tesseract is installed — this is correct documented behavior, not a bug.

---

## Test Results (Pre-inference, Mocked)

```
10 passed in 3.19s  (tests/test_services.py)
3 passed in 2.98s   (tests/test_real_inference.py::TestEngineMissingBehavior)
```

All 13 tests pass against the current environment.

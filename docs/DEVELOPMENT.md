# Development

## Prerequisites

- Windows 11, Node.js 20.9+, npm.
- Python 3.11 recommended. No GPU or model download is needed.

## Backend

From `backend`, create and activate a virtual environment, install `requirements.txt`, copy `.env.example` to `.env`, and run `uvicorn app.main:app --reload`. The SQLite database and upload directory are relative to the backend working directory by default. The service listens at `http://localhost:8000`; interactive docs are at `/docs`.

Run the analysis worker in a second backend terminal with `python -m app.worker`. It is not started by the API. Optional OCR and detection setup, weight download, configuration, and licenses are documented in [PHASE_03_MODELS.md](PHASE_03_MODELS.md). An unavailable engine is persisted as a failed task; the API still supports uploads and research records.

## Frontend

From project root, run `npm install`, copy `.env.example` to `.env.local`, then `npm run dev`. The app listens at `http://localhost:3000`. Set `NEXT_PUBLIC_API_URL` before starting the frontend if the API is elsewhere.

## Quality checks

From the project root, run `npm test`, `npm run typecheck`, `npm run lint`, and `npm run build`. Frontend tests use Vitest, jsdom, and React Testing Library for navigation, upload selection/preview/validation, submission states, history pagination, results, and forensics rendering.

From `backend`, run `python -m pytest`. Service tests run without a local server. Real HTTP integration tests in `tests/test_api.py` use FastAPI's TestClient and a temporary SQLite database. Enable them in PowerShell with `$env:ISQUARE_RUN_HTTP_TESTS='1'; python -m pytest tests/test_api.py`.

## Manual image-to-record verification

1. Start FastAPI and Next.js in separate terminals using the commands above.
2. Open `http://localhost:3000`, then choose **New Research**.
3. Select a real JPEG, PNG, or WEBP below 10 MB. Confirm the local preview, filename, and size.
4. Optionally enter context, then select **Start Analysis**. Confirm the upload and record-creation progress, then the result route.
5. Check the returned dimensions, MIME type, file size, and SHA-256 on the result page. Confirm the state remains `queued` and all analysis sections say they have not run.
6. Open **History**, confirm the record and image preview, then refresh. The record should load again from SQLite.
7. Open **Image Forensics**, select the same image, and select **Inspect image**. Confirm file facts, SHA-256, and available EXIF fields. No AI detection score should appear.
8. To inspect lifecycle transitions directly, use `PATCH /api/v1/research/{id}/status` in `/docs`; try `queued → processing → completed`, and verify an invalid transition returns 409 and an unknown status returns 422. These transitions only update workflow status; they do not run analysis.

## Phase 03B analysis verification (inference operational)

**Phase 03B status (2026-11-14):**

| Engine | Status |
|---|---|
| PyTorch 2.15.0+cpu | ✅ Installed |
| Torchvision 0.29.2+cpu | ✅ Installed |
| SSDLite COCO weights | ✅ Downloaded (13.42 MB) |
| Object detection (real) | ✅ Executed — 94–186 ms warm inference |
| pytesseract 0.3.13 | ✅ Installed |
| Tesseract 5 binary | ⚠️ Not installed — manual step required |
| OCR real inference | ⚠️ Deferred — install Tesseract to enable |

Use the three-terminal API/worker/frontend workflow. See [PHASE_03B_SETUP.md](PHASE_03B_SETUP.md) for the complete setup procedure including the Tesseract Windows installer steps.

**Running real inference tests:**

```powershell
cd c:\project\phase2\isquare2\backend

# All tests (without Tesseract: 20 passed, 9 skipped)
python -m pytest tests/ -v

# Detector only (always works after weight download)
python -m pytest tests/test_real_inference.py::TestDetectorRealInference -v -s

# OCR (requires Tesseract binary — skipped if absent)
python -m pytest tests/test_real_inference.py::TestOCRRealInference -v -s
```

See [PHASE_03B_TESTING.md](PHASE_03B_TESTING.md) for the full test reference and [PHASE_03B_INFERENCE_RESULTS.md](PHASE_03B_INFERENCE_RESULTS.md) for measured benchmark results.

## Troubleshooting

- Frontend network errors: confirm the API is running and `NEXT_PUBLIC_API_URL` is correct.
- CORS errors: set backend `FRONTEND_ORIGIN` to the exact browser origin, then restart.
- PowerShell blocks virtualenv activation: use `py -3.11 -m venv .venv`; alternatively invoke `.venv\Scripts\python.exe -m uvicorn app.main:app --reload` without activation.
- Upload rejected: only real JPEG, PNG, or WEBP images up to 10 MB and 40 megapixels are accepted.

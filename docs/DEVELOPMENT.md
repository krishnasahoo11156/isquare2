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

## Phase 03 analysis verification

Use the three-terminal API/worker/frontend workflow and model requirements in [PHASE_03_TESTING.md](PHASE_03_TESTING.md). Analysis is queued via the Results page or API and only advances when the worker claims it. The manual status PATCH is retired (410). The result page polls while queued/processing, stops at a terminal state, and reads persisted module output. Model output availability depends on separately installed local engines and weights.

## Environment verification limit

In this Codex Windows sandbox, Python 3.13's asyncio Proactor loop blocks in `_make_self_pipe` while falling back to a loopback `socketpair`; a minimal `socket.socketpair()` probe also blocks. FastAPI TestClient therefore cannot execute requests here, and this environment cannot perform a live browser-to-backend test. The HTTP tests are retained and opt-in for an unrestricted local Windows environment. Playwright is not installed; UI states are covered with jsdom component/page tests. Use the manual workflow above on the target machine to complete the real-browser verification.

For Phase 03, model execution is also not available in this environment: Python 3.13.14 has Pillow and NumPy but not Torch/Torchvision/pytesseract, no Tesseract executable or language data, and no downloaded weights or evaluation dataset. No real inference, accuracy benchmark, or browser-to-worker roundtrip is claimed. See [PHASE_03_TESTING.md](PHASE_03_TESTING.md).

## Troubleshooting

- Frontend network errors: confirm the API is running and `NEXT_PUBLIC_API_URL` is correct.
- CORS errors: set backend `FRONTEND_ORIGIN` to the exact browser origin, then restart.
- PowerShell blocks virtualenv activation: use `py -3.11 -m venv .venv`; alternatively invoke `.venv\Scripts\python.exe -m uvicorn app.main:app --reload` without activation.
- Upload rejected: only real JPEG, PNG, or WEBP images up to 10 MB and 40 megapixels are accepted.

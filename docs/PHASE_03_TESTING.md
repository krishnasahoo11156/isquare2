# Phase 03 Testing and Verification

## Automated checks

Backend tests run direct service/SQLite calls and include EXIF orientation without source mutation, idempotent analysis row creation, worker lease claim, independent module failure, OCR-shaped partial persistence, and the Phase 02 image/storage/database checks. They do not call the local HTTP listener in this sandbox.

```powershell
cd C:\project\phase2\isquare2\backend
python -m pytest -q -p no:asyncio
```

The 8 FastAPI TestClient cases remain opt-in because this Windows sandbox blocks the Proactor event loop's loopback socketpair. On a normal Windows machine, also run:

```powershell
$env:ISQUARE_RUN_HTTP_TESTS = '1'
python -m pytest tests\test_api.py -q
```

Frontend checks:

```powershell
cd C:\project\phase2\isquare2
npm test -- --reporter=dot
npm run typecheck
npm run lint
npm run build
```

Frontend component/page tests mock API methods and are not end-to-end evidence. Playwright is not installed in this environment.

## Local end-to-end procedure

Use three PowerShell terminals from the project directory:

```powershell
cd C:\project\phase2\isquare2\backend
python -m uvicorn app.main:app --reload
```

```powershell
cd C:\project\phase2\isquare2\backend
python -m app.worker
```

```powershell
cd C:\project\phase2\isquare2
npm run dev
```

1. Install/configure optional engines per `PHASE_03_MODELS.md`; confirm `tesseract --list-langs` and the model weight file before expecting inference.
2. In the browser, open `http://localhost:3000`, select **New Research**, choose an authorized supported image, and submit with the analysis checkbox enabled.
3. Confirm the result page first reports queued/processing, then reaches completed or failed based on actual worker task results. Do not expect an analysis result when the worker is stopped.
4. Confirm task status, OCR output or explicit empty result, object detections if the model is installed, classifier uncertainty, and model execution records. Do not expect unsupported tasks to appear successful.
5. Open History and Results after a refresh. Restart API and worker and confirm the same analysis/result rows load from SQLite.
6. With Tesseract enabled, test known printed text at multiple regions and compare output against hand-verified transcription; inspect overlay coordinate alignment. Include rotated EXIF images and difficult/no-text cases.
7. With detector weights installed, use a separately labeled fixture and verify categories/boxes; report misses and false positives, not just successful examples.
8. Induce a missing model and an OCR failure separately. Confirm successful sibling-task data remains and warnings state which task failed. Stop a worker during a sufficiently long local job to exercise lease recovery and retry bounds.
9. Use `/docs` to inspect `POST /api/v1/research/{id}/analyze`, results/status, retry, and the retired status endpoint (410). Verify duplicate analyze calls do not create another active job.

## Checks completed in this workspace

| Check | Result |
|---|---|
| Backend service/model/evaluation tests | 11 passed, 9 HTTP tests skipped by default |
| Opt-in FastAPI HTTP integration | 9 passed, including queue idempotency, status/results retrieval, dashboard counts, legacy status rejection, image upload, and research persistence |
| Frontend component/page tests | 15 passed (rerun after final image-preview/nav correction below) |
| TypeScript and ESLint | Passed (rerun after final UI correction below) |
| Production frontend build | Passed; 7 routes generated |
| Real browser flow | Uploaded a generated non-personal PNG through the page; backend created the stored image/research/analysis; worker reported actual unavailable engines; History showed it; refresh and reopening the result retained the failed analysis and task error codes |

This proves the local API/worker/frontend wiring and honest missing-model behavior. It does not prove OCR recognition or object-detection accuracy. The last browser run preceded a small final Results-page preview/sidebar-label adjustment; those final UI changes passed component tests, TypeScript, lint, and the production build but were not repeated through CUA.

## Current environment and remaining verification

Python 3.13.14 is available (not the documented Python 3.11 baseline). Pillow and NumPy are installed; `torch`, `torchvision`, `pytesseract`, OpenCV, PaddleOCR, and the Tesseract executable are absent. No model weights or licensed test images are present. Consequently no real OCR/detector inference or accuracy benchmark has been run here. The browser did verify the worker's actual model-unavailable failure state, but not successful model inference or worker recovery after a process restart. Run the procedure above after installing the engines on an unrestricted local machine.

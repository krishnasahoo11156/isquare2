# iSquare Phase 02 Verification

## Corrections completed

- Added a centralized validated backend settings object and shared response schemas for upload metadata, research context, lifecycle state, and pagination.
- Enabled SQLite foreign-key checks and normalized SQLite timestamps back to timezone-aware UTC.
- Added sequential SHA-256 upload deduplication, bounded EXIF response fields, structured upload/storage errors, cleanup after failed writes/commits, dynamic upload-limit messages, and cached orientation-correct thumbnail responses.
- Added a validated job lifecycle: `queued → processing|failed`, `processing → completed|failed`, `failed → queued`, and `completed` terminal. Upload only creates `queued` records.
- Added `PATCH /api/v1/research/{research_id}/status`; Pydantic rejects unknown states and service rules reject invalid transitions. This route is unauthenticated and intended for local development only.
- Centralized frontend types and methods for metadata, typed research creation, status changes, and list pagination. History pages through 20 records; Dashboard reads the API total and requests only its five recent rows.
- Corrected image replacement errors to clear invalid selections, revoke preview URLs on teardown, show missing-thumbnail fallback, display stored context/current status, and keep the completed status separate from analysis claims.
- Added Vitest/React Testing Library page and component tests, plus actual FastAPI TestClient integration tests using a temporary database and storage directory.

## Test results

Executed in the provided Windows sandbox with Node.js 24.14.1, npm 11.11.0, and Python 3.13.14.

| Check | Result |
|---|---|
| `npm test -- --reporter=dot` | Passed: 14 tests across 2 files |
| `npm run typecheck` | Passed |
| `npm run lint` | Passed with no warnings |
| `npm run build` | Passed; all six application routes emitted |
| `python -m pytest -q -p no:asyncio --basetemp=.pytest-phase02-backend-final` | Passed: 6 service/model/contract tests; 8 HTTP tests skipped |

Frontend tests cover navigation, image selection/preview/invalid-file feedback, 10 MB feedback, disabled/loading submission, upload errors, record creation navigation, metadata display, history pagination, result fields/status, dashboard totals, empty states, and broken-thumbnail fallback. UI tests mock the API layer; they do not substitute for the unrun backend/browser workflow.

Backend service tests cover SHA-256, duplicate reuse, EXIF extraction, dimensions, image preview generation, safe lifecycle transitions, pagination functions, UTC timestamp round-tripping, SQLite foreign keys, missing-record behavior, storage failure responses, and the generated OpenAPI lifecycle contract. Eight TestClient tests are present for health, upload, hash/metadata/thumbnail response, duplicate upload, invalid/oversized image, storage failure, research/pagination/not-found, persistence, and status transitions.

## End-to-end verification limit

The eight HTTP tests are gated by `ISQUARE_RUN_HTTP_TESTS=1` because the sandbox cannot start Python’s Windows asyncio event loop. A minimal FastAPI TestClient request hung in `asyncio.ProactorEventLoop._make_self_pipe`, which fell back to `socket.socketpair()` and blocked in `socket.accept()`. A direct `socket.socketpair()` probe also hung; an attempted local service start was rejected with “An attempt was made to access a socket in a way forbidden by its access permissions.” Playwright is not installed, and this same loopback restriction prevents browser-to-API verification here.

The suite is ready to run on a normal local Windows machine with:

```powershell
cd backend
$env:ISQUARE_RUN_HTTP_TESTS = '1'
python -m pytest tests/test_api.py -q
```

## Manual browser verification

On the target machine, run the backend and frontend in separate terminals. Open `http://localhost:3000`, go to **New Research**, select a real supported image, verify the preview, submit, then confirm the results page shows backend dimensions/hash and a `queued` status. Open **History**, refresh the browser, and reopen the record. Go to **Image Forensics**, inspect the same file, and verify dimensions, MIME type, SHA-256, and available EXIF data. No AI score or research findings should appear.

API documentation is at `http://localhost:8000/docs`. The former manual workflow-state PATCH now returns 410; only the analysis worker owns processing/completion status.

## Remaining limitations

- The full browser-to-backend workflow and persistent record across a browser refresh were not observed in this sandbox. Perform the manual sequence above on an unrestricted local environment.
- Python 3.11 was not available; Python tests ran under 3.13.14.
- The status update route has no authentication. Keep FastAPI local; add worker/operator authentication before exposing it on a network.
- Duplicate detection is sequential and does not include a unique database constraint, so concurrent identical uploads may still race. Adding a uniqueness constraint to an existing Phase 01 database should be done through a verified Alembic migration.
- No retention/delete policy exists. Image files and records remain until a deliberate retention policy is implemented.
- No worker performs AI analysis, OCR, provenance checks, or authorized public-source research. The status API only updates workflow state.

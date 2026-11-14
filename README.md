# iSquare

**Visual Intelligence & Digital Research Engine** — an image-first workspace for building evidence-led research. The application supports local image analysis with an independent CPU worker. OCR and object detection are optional local engines; unsupported or missing models are reported instead of simulated.

## Implemented

- Responsive light-first Next.js workspace with Dashboard, New Research, Research Results, Image Forensics, History, and Settings.
- FastAPI image intake for JPEG, PNG, and WEBP with content decoding, 10 MB limit, dimension cap, UUID storage, and SHA-256.
- SQLite records for uploaded images and queued research jobs.
- Worker-owned research lifecycle (`queued`, `processing`, `completed`, `failed`) with a leased SQLite analysis queue and explicit retry.
- SHA-256 duplicate uploads reuse the existing image asset rather than writing another copy.
- Paginated history and accurate dashboard total counts.
- Real frontend upload and record creation, with API errors shown to the user.
- File metadata and EXIF inspection.
- Persisted analysis/task records, normalized OCR blocks and detections, evidence-linked observations, and a results API/UI. Classification remains uncertain until a validated iSquare taxonomy model is available.

## Stack

- Next.js 16, React 19, TypeScript 5, Tailwind CSS 4, Lucide React.
- Python FastAPI, Pydantic 2, SQLAlchemy 2, Pillow, Uvicorn, SQLite.
- PyTorch 2.15.0+cpu, Torchvision 0.29.2+cpu (object detection, CPU-only).
- pytesseract 0.3.13 + Tesseract 5 (OCR, requires separate Windows binary install).
- Vitest and React Testing Library for frontend interaction tests.
- Python 3.13.14 (confirmed); Python 3.11 is the documented baseline.

## Setup

Backend (PowerShell):

```powershell
cd backend
python -m pip install -r requirements.txt
python -m pip install -r requirements-analysis.txt
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
Copy-Item .env.example .env
# Download detector weights (one-time, ~13 MB):
python -m app.services.analysis.download_models
uvicorn app.main:app --reload
```

Install Tesseract 5 for Windows separately (see [docs/PHASE_03B_SETUP.md](docs/PHASE_03B_SETUP.md)) to enable OCR.

Start the worker in another backend terminal:

```powershell
cd backend
python -m app.worker
```

Frontend (second terminal, project root):

```powershell
npm install
Copy-Item .env.example .env.local
npm run dev
```

The frontend `.env.example` sets `NEXT_PUBLIC_API_URL=http://localhost:8000`. Open <http://localhost:3000>; API docs are at <http://localhost:8000/docs>.

## Quality checks

```powershell
npm test
npm run typecheck
npm run lint
npm run build
```

From `backend`, run `python -m pytest`. Real FastAPI HTTP integration tests are in `backend/tests/test_api.py`; enable them with `$env:ISQUARE_RUN_HTTP_TESTS='1'` before running pytest on a machine that permits Python's local asyncio sockets.

## API overview

- `GET /` — application information.
- `GET /api/v1/health` — service status and version.
- `POST /api/v1/images/upload` — multipart image upload.
- `GET /api/v1/images/{image_id}/metadata` — stored file and EXIF metadata.
- `GET /api/v1/images/{image_id}/thumbnail` — stored image content for the local workspace.
- `POST /api/v1/research` — create a queued record from an uploaded image and optional context.
- `GET /api/v1/research?limit=20&offset=0` — paginated records.
- `GET /api/v1/research/{research_id}` — one record.
- `POST /api/v1/research/{research_id}/analyze` — idempotently queue image analysis.
- `GET /api/v1/research/{research_id}/analysis` and `/analysis/status` — retrieve persisted output and task lifecycle.
- `POST /api/v1/research/{research_id}/analysis/retry` — retry a failed attempt within its configured limit.
- `GET /api/v1/analysis/{analysis_id}` and `/api/v1/analysis/summary` — analysis record and actual dashboard counts.
- `PATCH /api/v1/research/{research_id}/status` — retired; returns 410 because only the worker may advance status.

## Architecture and security

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md), [docs/PHASE_02_AUDIT.md](docs/PHASE_02_AUDIT.md), [docs/PHASE_02_TESTING.md](docs/PHASE_02_TESTING.md), and the four Phase 03 documents. Uploads are stored outside the public frontend tree; model outputs live in SQLite. The service does not identify unknown people, scrape social media, or infer private details.

## Roadmap

Known Phase 03 limitations and the unrun model evaluation are documented in `docs/PHASE_03_EVALUATION.md` and `docs/PHASE_03_TESTING.md`. No AI result is synthesized when an engine is unavailable.

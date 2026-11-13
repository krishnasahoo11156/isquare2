# iSquare

**Visual Intelligence & Digital Research Engine** — an image-first workspace for building evidence-led research. Phase 01 establishes safe image intake, verifiable file metadata, and persistent research records. It does not perform AI analysis or external-source research.

## Implemented

- Responsive light-first Next.js workspace with Dashboard, New Research, Research Results, Image Forensics, History, and Settings.
- FastAPI image intake for JPEG, PNG, and WEBP with content decoding, 10 MB limit, dimension cap, UUID storage, and SHA-256.
- SQLite records for uploaded images and queued research jobs.
- Real frontend upload and record creation, with API errors shown to the user.
- File metadata and EXIF inspection; analysis sections clearly marked as not yet analyzed.

## Stack

- Next.js 16, React 19, TypeScript 5, Tailwind CSS 4, Lucide React.
- Python FastAPI, Pydantic 2, SQLAlchemy 2, Pillow, Uvicorn, SQLite.
- Use Node.js 20.9+ and Python 3.11 (Python 3.13 may also work; dependencies should be installed and checked locally).

## Setup

Backend (PowerShell):

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

Frontend (second terminal, project root):

```powershell
npm install
Copy-Item .env.example .env.local
npm run dev
```

The frontend `.env.example` sets `NEXT_PUBLIC_API_URL=http://localhost:8000`. Open <http://localhost:3000>; API docs are at <http://localhost:8000/docs>.

## API overview

- `GET /` — application information.
- `GET /api/v1/health` — service status and version.
- `POST /api/v1/images/upload` — multipart image upload.
- `GET /api/v1/images/{image_id}/metadata` — stored file and EXIF metadata.
- `GET /api/v1/images/{image_id}/thumbnail` — stored image content for the local workspace.
- `POST /api/v1/research` — create a queued record from an uploaded image and optional context.
- `GET /api/v1/research?limit=20&offset=0` — paginated records.
- `GET /api/v1/research/{research_id}` — one record.

## Architecture and security

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md). Uploads are stored outside the public frontend tree; the database stores a path plus image facts, not duplicate image bytes. Phase 01 does not identify unknown people, scrape social media, or infer private details. Future public-source claims must retain source URLs, timestamps, supporting evidence, verification status, and uncertainty.

## Roadmap

Future phases may add authorized research connectors, OCR, provenance tooling, evidence correlation, contradiction detection, and report generation. No model is downloaded or loaded in this phase.

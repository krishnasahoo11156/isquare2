# Architecture

## System

Next.js App Router provides the desktop-first responsive interface. A centralized TypeScript API layer communicates with FastAPI over HTTP. FastAPI owns validation, image storage, and persistence. SQLite is the Phase 01 database; local uploads remain in `backend/storage/uploads` and are never served as a static frontend directory.

## Frontend

`src/app` contains all six routes and shared global layout. `src/components/layout` provides navigation; `src/components/research` handles image selection and preview; `src/components/shared` contains record views. `src/lib/api` centralizes HTTP calls and typed research models. Pages distinguish loading, error, empty, and queued states.

## Backend

`app/api/routes` exposes health, image, and research endpoints. Image decoding and dimension checks live in `app/services/image_service.py`; random safe file storage lives in `storage_service.py`; job creation and status transition rules live in `research_service.py`. SQLAlchemy entities are in `app/models`; Pydantic API models in `app/schemas`; `app/core/config.py` validates environment configuration; `app/database/connection.py` configures SQLite and sessions.

## Data model

`image_assets` stores UUID, sanitized original name, random storage filename, detected MIME type, byte size, dimensions, SHA-256, storage path, and created timestamp. Sequential duplicate content reuses the existing image record by SHA-256. `research_jobs` stores UUID, title, image foreign key, optional context, lifecycle status, and created/updated timestamps. Relationships and indexes support image lookup, status filtering, and recent history. SQLite foreign-key enforcement is enabled per connection. A UTC datetime type restores aware UTC values on SQLite reads. Tables are initialized with SQLAlchemy metadata at service startup; no new columns were required for Phase 02, so Alembic remains deferred. Introduce Alembic before the first schema change that must upgrade an existing database.

## Upload and API flow

The browser validates MIME hint and file size for usability, previews a local object URL, then uploads bytes. The backend enforces size independently, decodes the image with Pillow, restricts detected format and pixel dimensions, hashes the exact bytes, reuses an existing matching asset or writes a random stored name, and commits image metadata. The image-content endpoint generates a small orientation-corrected JPEG preview and applies a short private cache lifetime instead of sending full-resolution uploads for history thumbnails. Research creation requires an existing image row. A record begins `queued`; no analysis is implied. `PATCH /api/v1/research/{research_id}/status` accepts only the defined transitions; it does not start analysis. The status route has no authentication and is for the local single-user development service only. Restrict it to a trusted worker or authenticated operator before making the API network-accessible. CORS is restricted to the configured frontend origin.

## Safety and future extension

The current local image-content route is intended for a single-user development workspace. Production deployment should add authentication, authorization, quotas, retention controls, and private object access. Future AI work should run asynchronously and persist execution records; evidence claims should retain source, retrieval time, excerpts, verification, and confidence. No identity matching of arbitrary people, private data inference, or unauthorized scraping is part of this architecture.

## Phase 03 local analysis

The Phase 03 extension preserves the existing upload and research entities, adds analysis/task/result tables, and queues work through `POST /api/v1/research/{id}/analyze`. `python -m app.worker` is a separate database-backed CPU worker; claim updates use a short compare-and-set transaction and an expiring lease. See [PHASE_03_ARCHITECTURE.md](PHASE_03_ARCHITECTURE.md) for task status, partial-result policy, privacy boundaries, and known incomplete engines. Model setup and license notes are in [PHASE_03_MODELS.md](PHASE_03_MODELS.md). The former status PATCH now returns 410; worker claims and result persistence own workflow transitions.

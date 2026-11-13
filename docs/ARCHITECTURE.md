# Architecture

## System

Next.js App Router provides the desktop-first responsive interface. A centralized TypeScript API layer communicates with FastAPI over HTTP. FastAPI owns validation, image storage, and persistence. SQLite is the Phase 01 database; local uploads remain in `backend/storage/uploads` and are never served as a static frontend directory.

## Frontend

`src/app` contains all six routes and shared global layout. `src/components/layout` provides navigation; `src/components/research` handles image selection and preview; `src/components/shared` contains record views. `src/lib/api` centralizes HTTP calls and typed research models. Pages distinguish loading, error, empty, and queued states.

## Backend

`app/api/routes` exposes health, image, and research endpoints. Image decoding and dimension checks live in `app/services/image_service.py`; random safe file storage lives in `storage_service.py`; initial job construction lives in `research_service.py`. SQLAlchemy entities are in `app/models`; Pydantic API models in `app/schemas`; `app/database/connection.py` configures SQLite and sessions.

## Data model

`image_assets` stores UUID, sanitized original name, UUID storage filename, detected MIME type, byte size, dimensions, SHA-256, storage path, and created timestamp. `research_jobs` stores UUID, title, image foreign key, optional context, queued status, and created/updated timestamps. Relationships and indexes support image lookup, status filtering, and recent history. Tables are initialized with SQLAlchemy metadata at service startup; Alembic is deferred until migration needs emerge.

## Upload and API flow

The browser validates MIME hint and file size for usability, previews a local object URL, then uploads bytes. The backend enforces size independently, decodes the image with Pillow, restricts detected format and pixel dimensions, generates a random stored name, hashes the exact bytes, and commits image metadata. Research creation requires an existing image row. A record begins `queued`; no analysis is implied. CORS is restricted to the configured frontend origin.

## Safety and future extension

The current local image-content route is intended for a single-user development workspace. Production deployment should add authentication, authorization, quotas, retention controls, and private object access. Future AI work should run asynchronously and persist execution records; evidence claims should retain source, retrieval time, excerpts, verification, and confidence. No identity matching of arbitrary people, private data inference, or unauthorized scraping is part of this architecture.

# iSquare Phase 02 Initial Audit

**Audit scope:** frontend routes and shared components, API client and types, FastAPI routes, Pydantic schemas, SQLAlchemy models and session setup, image validation/storage, configuration, tests, and existing documentation.

**Audit boundary:** this report records the implementation as found before Phase 02 changes. No application files were modified before this audit was completed.

## Existing architecture

- Next.js 16 App Router, React 19, strict TypeScript, Tailwind CSS 4, and a small global CSS design system. The six requested pages share a client-side navigation shell.
- A centralized fetch helper lives in `src/lib/api/client.ts`; research and image-upload methods/types live in `src/lib/api/research.ts`.
- FastAPI exposes health, upload, image metadata/content, and research CRUD-read endpoints. SQLAlchemy 2 maps `ImageAsset` and `ResearchJob`; Pydantic models describe upload and research responses.
- SQLite is initialized using `Base.metadata.create_all()` on application startup. Upload files are stored under a configured local directory using random names.
- Image parsing, file storage, hash calculation, and initial job construction have service/helper modules. CORS is configured for one frontend origin.

## What works correctly

- Frontend and backend both validate image type/size independently. The backend inspects actual decoded image content, permits JPEG/PNG/WEBP, caps uploads at 10 MB and dimensions at 40 megapixels, assigns a random storage name, and computes SHA-256.
- Image and research responses omit the server filesystem path. Image retrieval resolves a database record and checks the resolved file is directly inside the configured storage directory.
- Research creation requires a stored image. Reads use bounded pagination (`limit` 1–100, default 20), eager-load image relationships, order newest first, and return 404 for missing records.
- Database sessions are yielded through a dependency and closed in `finally`; upload commit failures attempt file cleanup and transaction rollback.
- The interface has explicit loading/error/empty states, a restrained light theme, responsive CSS, and no analysis claims presented as verified results.
- The prior frontend TypeScript/lint/build checks and two backend tests passed in this workspace. Those backend tests exercised Python functions directly, not HTTP requests.

## Bugs and incomplete behavior

1. **No HTTP or browser integration tests.** The existing tests call the health/upload/research route functions directly. They do not verify FastAPI routing, multipart parsing, response serialization, CORS, or a real browser upload-to-history flow. A prior local socket check was blocked by the execution sandbox; this limitation needs to be retested/documented in Phase 02.
2. **Research status is not a lifecycle.** The database has a free-form string defaulting to `queued`, with no state constraint or transition method/endpoint. The Results page hardcodes “Queued” even if a different status is ever stored; generic styling exists only for queued.
3. **History is truncated without navigation.** The UI always requests 50 rows, and the API already provides `total`, `limit`, and `offset`, but History has no next/previous controls. Dashboard also labels the number of fetched rows as the total record count, which undercounts once there are more than 50.
4. **Frontend API types are incomplete and scattered.** `Research` omits returned context fields and defines `status` as any string. Metadata is typed locally in the forensics page, while the API method is called inline. `createResearch` accepts an unvalidated `Record<string,string>`.
5. **New Research can orphan uploads.** The image upload commits before the research record is created. If record creation fails, retrying uploads the same bytes again; there is no duplicate-content behavior or cleanup policy for unused assets.
6. **Upload storage failures lack a deliberate response.** `mkdir`/`write_bytes` errors escape the route as generic server errors. File cleanup can itself fail and mask the original database exception. The configured size value is dynamic, but the error message is hardcoded to “10 MB”.
7. **Upload body resource use is only bounded after multipart parsing.** The route reads at most `MAX_BYTES + 1` from `UploadFile`, but a very large request may already have been accepted/spooled by the multipart parser before the endpoint applies this limit. An upstream/body-size limit or bounded streaming policy should be considered.
8. **SQLite referential integrity is not explicitly enabled.** The model declares a foreign key, but SQLite requires `PRAGMA foreign_keys=ON` per connection. Existing application logic checks the image before research creation, yet the database itself does not enforce the constraint.
9. **SQLite timezone behavior needs normalization.** Models create UTC-aware datetimes, but SQLite commonly returns naive datetimes for `DateTime(timezone=True)`. Responses and ordering should be tested for consistent UTC semantics.
10. **EXIF extraction is permissive but not bounded by field count.** Individual values are shortened, but the endpoint returns every EXIF entry. Invalid EXIF is caught; malformed metadata and very large tag collections need explicit tests/limits.
11. **Image preview state can be confusing.** Selecting an invalid replacement leaves the previous valid selection active while showing an error; object URLs are revoked on replacement/removal but not on component unmount.
12. **Results context is incomplete.** The page omits public profile URL and additional context, and repeats a hard-coded queued badge. The “not analyzed” notice is correct for Phase 01 but needs to remain independent from lifecycle state.

## Security and data-integrity concerns

- Current image content routing does not accept an arbitrary filesystem path and verifies database ownership of a path under the upload directory. The returned `FileResponse` should use inline content disposition for image previews rather than the default attachment behavior.
- Current validation correctly avoids trusting the original extension or client MIME type. The 40-megapixel check happens before full decode; tests should include corrupt files and decompression-bomb-like dimensions.
- Storage uses unpredictable filenames and stores outside the frontend tree. Upload duplication is currently allowed and produces additional files/rows; this is not inherently unsafe but has no documented policy.
- SQLite foreign-key enforcement is absent, startup schema creation is not a migration strategy, and no delete operation currently exists. There is no destructive cleanup policy, which avoids accidental file/reference deletion for now.
- The development API has no authentication. Any reachable caller can create records and retrieve stored image bytes/metadata. This is acceptable only for the intended local single-user setup; it must be addressed before networked deployment.
- `load_dotenv()` and direct `os.getenv()` calls are spread across modules rather than validated through one settings object. Configuration values such as storage path, max size, database URL, and CORS origin should be centralized and checked at startup.

## Frontend and product consistency

- The visual language is coherent: white/warm-neutral surfaces, thin borders, restrained monochrome icons, keyboard focus, and simple navigation. No redesign is warranted.
- Dashboard uses two independent API calls; the recent research request loads 50 records to display five. It can request a smaller page and use the API total for its summary.
- Forensics correctly displays actual returned metadata and honest future-state labels. Its metadata response is not represented in the shared API contract.
- Settings is intentionally read-only and does not present nonfunctional controls as working integrations.
- History thumbnails are rendered from the backend content route; broken image handling currently hides the image without a visible fallback.

## Tests and documentation

- The backend test suite contains two tests. It checks health configuration, a valid JPEG upload, SHA-256/dimensions, metadata route function behavior only indirectly, queued research creation/retrieval/listing, malformed-image rejection, upload-size rejection by reducing the configured threshold, and dimension rejection by reducing the service threshold.
- It does not cover actual HTTP requests, invalid/missing IDs at HTTP level, pagination boundaries, EXIF cases, storage failures, database persistence across app restarts, or status transitions.
- No frontend component/browser tests are present. `README.md`, `ARCHITECTURE.md`, and `DEVELOPMENT.md` describe Phase 01 and local startup, but not actual end-to-end verification, lifecycle semantics, API error contracts, or the sandbox network limitation.

## Recommended Phase 02 corrections

1. Add a real API-level integration test using an isolated SQLite database and temporary storage; attempt Playwright only if browser/local network access works in this environment.
2. Add an explicit validated lifecycle (`queued → processing → completed|failed`, with a deliberate retry rule) and never couple completion to upload. Surface the persisted state in the UI.
3. Use the pagination metadata in History and the total count in Dashboard; avoid fetching 50 rows just to show five.
4. Centralize TypeScript request/response types and methods, including metadata and status; define a narrow status union.
5. Enable SQLite foreign keys, normalize UTC timestamps in responses, and test persistence and constraints.
6. Structure storage failures and cleanup safely, make the upload limit message reflect configuration, and set image content disposition inline.
7. Add tests for missing resources, pagination, storage failures, EXIF/no-EXIF, and lifecycle transitions. Keep deletion/retention policy explicit before implementing cleanup.
8. Preserve the existing visual design and fix only the preview replacement/unmount behavior, status presentation, thumbnail fallback, and incomplete result context.

## Confirmed limitations at audit time

- No worker performs image analysis, OCR, provenance validation, AI-generated image detection, or public-source research.
- A real browser-to-API run and loopback request could not be established during Phase 01 due the then-current execution sandbox restrictions. Phase 02 must record the exact result of a fresh attempt and provide manual steps if the restriction remains.
- The workspace runtime is Python 3.13, not the documented Python 3.11 target; the pinned backend packages installed and tests ran under 3.13, but 3.11 still requires verification.

## Post-audit disposition

The findings above describe the pre-change state. Phase 02 corrections and test evidence are recorded in [PHASE_02_TESTING.md](PHASE_02_TESTING.md). In brief, pagination/totals, typed contracts, lifecycle transitions, SQLite foreign keys/UTC reads, storage error handling, duplicate reuse, thumbnail sizing, and frontend selection/status behavior have been corrected. HTTP-level verification and real-browser upload remain unverified because the local asyncio/loopback socket restriction blocks requests in this sandbox; follow the documented manual workflow on a normal local machine.

# Phase 03 Initial Codebase Audit

**Audit completed before Phase 03 code changes.** The Phase 02 workspace already contained a Next.js frontend, FastAPI backend, SQLite models for `ImageAsset` and `ResearchJob`, local image storage, typed upload/research API methods, and UI tests. No analysis code or model dependencies were present.

## Architecture and working foundation

- `ResearchJob.image_id` links an existing research record to a stored `ImageAsset`; the original image stays in the existing storage directory.
- The API has bounded research list pagination, image validation, SHA-256 deduplication, and typed research responses.
- The Results page already fetches the persistent research record, and the UI uses the established light, minimal design.
- Backend database tables are initialized with `Base.metadata.create_all()`. SQLite foreign keys are enabled, but there is no migration framework.
- API integration tests are gated because the current sandbox blocks Windows loopback sockets. Python in this workspace is 3.13.14; Phase 02 documentation targets Python 3.11.

## Phase 03 gaps and risks found

1. No analysis tables, job queue, worker process, preprocessing service, OCR, classifier, detector, model manager, or persisted results API existed.
2. `PATCH /api/v1/research/{id}/status` permits callers to transition `queued → processing → completed` without running analysis. That is incompatible with an analysis-owned lifecycle and could present false completion.
3. The New Research screen creates a record but only navigates; no analyze request exists. The Results page contains only record metadata and no persisted analysis sections. Dashboard counts research rows only.
4. No inference dependencies, binaries, weights, model cache configuration, or model installation instructions existed. The local environment has Python 3.13, Pillow, and NumPy; it has no PyTorch, torchvision, Tesseract executable, pytesseract, OpenCV, ONNX Runtime, or PaddleOCR.
5. Phase 02's `ResearchJob` lifecycle strings can be transitioned through service rules, but there is no lease, claim, retry counter, or recovery policy for a worker.
6. Existing auto-created schema has no migration mechanism. Adding tables is backward-compatible for existing records, but any change to existing columns would need a real migration.
7. Existing frontend uses mocked API tests; no browser-to-backend run is available in this sandbox. A model result cannot be truthfully claimed until inference has run on licensed fixtures with ground truth.

## Candidate evaluation (design-time)

- **OCR:** Tesseract 5 with English `tessdata_fast` and the small `pytesseract` adapter is selected as an optional local CPU engine. Tesseract is Apache-2.0 and has documented Windows installers; its trained-data packages must be installed separately. It supplies word boxes and confidence but language, handwriting, rotated-text, and difficult-scene quality are limited. No engine is bundled or silently downloaded.
- **General classification:** Torchvision MobileNetV3-Small is lightweight relative to larger CNNs, CPU-capable, and uses ImageNet weights; however, its 1,000 ImageNet labels are not iSquare's 11 requested categories. No unsupported label mapping will be made. A validated iSquare category head/dataset is unavailable, so classification will report unavailable/uncertain until there is a sourced, evaluated model.
- **Detection:** Torchvision SSDLite320 MobileNetV3 is a compact COCO detector and avoids Ultralytics' AGPL-3.0 licensing choice, but PyTorch/torchvision add substantial install/RAM cost and Windows wheel compatibility must be verified for the selected Python. Weights are not present here. Detection remains an optional adapter, unavailable until explicitly installed and executed. No face recognition is planned.
- No model/library has been installed and no accuracy or speed benchmark is claimed in this audit. Evaluation scripts and a lawful held-out dataset are prerequisites for any confidence claim.

## Implementation strategy

Additive analysis tables and a SQLite compare-and-set worker queue will preserve existing records. The worker will load optional engines lazily, use short claim/result transactions, record per-task outcomes, and never claim a completed job when all modules fail. API requests will queue work; they will not run inference. Original files remain untouched. Existing unrestricted status mutation will be retired in favor of worker-owned transitions. Missing dependencies should produce durable task errors and leave upload/history available.

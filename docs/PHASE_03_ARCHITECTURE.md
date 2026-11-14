# Phase 03 Analysis Architecture

## Implemented flow

The existing `ImageAsset` and `ResearchJob` remain the source of truth. `POST /api/v1/research/{id}/analyze` validates the existing record and file, then inserts one `ImageAnalysis` row (unique on research ID and analysis version). The request returns without inference. A separate process (`python -m app.worker`) claims queued rows with a conditional SQLite update and a time-limited lease. It performs bounded EXIF-oriented RGB preprocessing and invokes independent classification, object-detection, and OCR adapters. Optional engines load lazily in the worker and are never loaded by FastAPI startup.

The selected object detector is Torchvision SSDLite320 MobileNetV3 Large COCO V1. It is CPU-only, has a 320-pixel detector input, 3.44 million parameters, 0.58 GFLOPS, and a documented 13.4 MB weight file. It returns COCO object labels and pixel boxes. Torch/Torchvision are optional and the weights are installed only by an explicit command. Inference uses one CPU thread and one worker process by default. A provisional score cutoff of 0.35 is used to suppress weak detections; it is **not calibrated** and must not be read as accuracy or probability of correctness.

Tesseract is an optional local OCR engine, called with pytesseract only when configured. It emits ordered word blocks and pixel boxes. Preprocessing applies EXIF orientation, RGB normalization, bounded downscaling, and a grayscale OCR view. Low-contrast images get one contrast adjustment; no thresholding or deskew is applied automatically. The original upload is unchanged. Coordinates use the EXIF-oriented analysis image dimensions returned with results. The UI requests an orientation-correct preview and positions OCR rectangles as percentages of those same dimensions.

Classification deliberately returns an unavailable/uncertain task state. ImageNet MobileNet labels do not directly equal iSquare's requested taxonomy, and there is no validated iSquare-trained head or suitable held-out dataset in this repository. No arbitrary label mapping or fabricated category is made. The adapter seam is ready for a properly sourced and evaluated model.

## Persistence and lifecycle

Additive tables store analyses, one classification result, multiple object detections, one OCR result plus ordered text blocks, evidence-linked observations, and per-task executions. Image bytes remain in the existing storage directory. Adding tables with `create_all` preserves Phase 02 databases and user records; no existing columns were altered. Before any existing-column change, adopt Alembic and test an upgrade against a copy of an existing SQLite file.

`ResearchJob.status` is now driven by worker claims and finalization. The old status PATCH remains documented but returns 410. An analysis is `completed` when at least one configured task succeeds; failed optional tasks remain visible in `task_statuses` and warnings. If every task fails, the analysis and research record become `failed`. An OCR result with empty text is a successful no-readable-text result. A failed analysis can be explicitly retried while under the configured attempt limit; successful earlier outputs remain until a replacement for that task commits.

The worker holds short transactions only for claiming and saving. A lease lets another process recover a job after a worker process stops; reaching the configured attempt limit marks an expired claim failed. An individual model exception is recorded as a task error, not a stack trace in the API. Current storage and SQLite setup remains single-machine/local-first. It is not a multi-host distributed queue, and crash/recovery behavior still needs subprocess-level integration testing on unrestricted Windows.

## Trust and privacy boundaries

Human presence is reported only when the COCO detector runs and emits the `person` label. No match produces the qualified statement “No person detected by the selected model.” Detection does not identify people. OCR text is stored as extracted model output, is not summarized or corrected, and can contain sensitive data; it is not logged. API and database outputs never include storage filesystem paths. Protect the local-only API with authentication, retention controls, and authorization before network exposure.

## Intentionally incomplete

- No iSquare taxonomy classifier or calibrated confidence interpretation.
- No object-detection model is bundled, fetched on startup, or executed in this environment yet.
- No real Tesseract executable or language pack is present in the current environment; OCR adapter execution is therefore not verified here.
- No labeled, licensed held-out evaluation corpus or benchmark result is included.
- No GPU, distributed queue, external analysis API, caption model, or identity recognition is used.

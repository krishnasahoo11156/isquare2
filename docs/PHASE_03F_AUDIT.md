# Phase 03F Initial System Audit & Operational Baseline

## 1. Executive Summary

Phase 03F conducted an architectural, algorithmic, and operational audit of the entire image intelligence system across backend services, model weights, data storage, database migrations, and frontend display interfaces.

---

## 2. Component-by-Component Audit

### 2.1 Classification Architecture
- **Backbone**: MobileNetV3-Large pre-trained feature trunk (`backbone.features`), frozen weights from `ssdlite320_mobilenet_v3_large-coco_v1.pth`, 480-dimensional pooled embedding.
- **Head Checkpoint v1**: `backend/storage/models/isquare_classifier_head_v1.pth` (248.1 KB, 2-layer MLP without batch normalization).
- **Head Checkpoint v2**: `backend/storage/models/isquare_classifier_head_v2.pth` (515.2 KB, 3-layer MLP with BatchNorm1d and Dropout, trained on real-world landscape crops and augmented photographs).
- **Image Information Gate**: `assess_image_information()` in `app/services/analysis/engines.py` gates inputs before inference:
  - Blank images ($\sigma < 2.5$) $\rightarrow$ `Uncertain` (confidence: 0.0)
  - Low-information images ($V_{\text{lap}} < 1.5, \sigma < 12.0$) $\rightarrow$ `Uncertain` (confidence: 0.0)
- **Uncertainty Gating**: Shannon entropy ceiling ($H(P) \le 1.85$), confidence floor ($p_{(1)} \ge 0.35$), ambiguous margin threshold ($\Delta p \ge 0.08$).

### 2.2 Object Detection Architecture
- **Engine**: SSDLite320 MobileNetV3 Large (`torchvision.models.detection.ssdlite320_mobilenet_v3_large`).
- **Weights**: Pre-trained COCO V1 checkpoint (`ssdlite320_mobilenet_v3_large-coco_v1.pth`, 13.42 MB).
- **Threshold**: Calibrated from provisional 0.35 to production **0.45** (eliminates vector graphic false positives while retaining 100% recall on real camera people and objects).
- **Threading**: Single worker process; 1 thread default (sub-70 ms latency on AMD Ryzen 7).

### 2.3 Optical Character Recognition (OCR)
- **Library**: `pytesseract` version `0.3.13` installed in virtual environment.
- **Binary Status**: Tesseract C++ executable is not pre-installed on this host (`ocr_engine_missing`).
- **Resilience**: Handled via partial-success policy (`overall_status = 'completed'` with transparent task failure warning).

### 2.4 Database & Persistence
- **Storage**: SQLite database at `backend/isquare.db`.
- **Automatic Migration**: `init_db()` in `app/database/connection.py` auto-migrates missing columns (`image_width`, `image_height`) idempotently on startup.
- **Entities**: `image_assets`, `research_jobs`, `image_analyses`, `classification_results`, `detection_results`, `ocr_results`, `visual_observations`, `model_executions`, `ocr_text_blocks`.

### 2.5 Frontend Integration
- **Framework**: Next.js 14 / React with Tailwind CSS.
- **Results Canvas**: Renders image with scaled object detection bounding boxes, category badge, visual observation cards, and honest task status indicators.
- **CORS Handling**: Direct allowlist for `http://localhost:3000` and `http://127.0.0.1:3000` with CORS headers attached to both 2xx/4xx and 500 error responses.

# Phase 03 Models and Installation

## Candidate decision

| Task | Choice | Why | License / limits |
|---|---|---|---|
| OCR | Tesseract 5 + `pytesseract` + `tessdata_fast` | Local CPU engine, word boxes/confidences, Windows installer, compact per-language data | Engine and fast traineddata Apache-2.0. Printed text is the target; multilingual capability exists only for explicitly installed and tested packs. Handwriting and difficult photographs can perform poorly. |
| Object detection | Torchvision `ssdlite320_mobilenet_v3_large`, COCO V1 | Compact CPU model (3.44M params, 0.58 GFLOPS, documented 13.4 MB weights), COCO categories include people and everyday objects | Torchvision code BSD-3-Clause. Review the model card/COCO data terms for your use. COCO detector has known domain limits. Model confidence is not calibrated. |
| iSquare category classification | Deferred; result is uncertain | Generic ImageNet labels cannot be honestly equated with “document”, “screenshot”, “logo”, etc. No licensed labeled iSquare dataset or custom head is present. | No mapping or training claim is made. MobileNetV3-Small was considered and rejected as a direct category predictor for this reason. |
| Alternative detector | Ultralytics YOLO nano variants | Compact CPU option | Not selected because model distribution has AGPL-3.0/Enterprise licensing choices; adding it without an explicit license decision is inappropriate. |

Official references: [Torchvision SSDLite model and published size/metrics](https://docs.pytorch.org/vision/main/models/generated/torchvision.models.detection.ssdlite320_mobilenet_v3_large.html), [Torchvision BSD-3-Clause repository](https://github.com/pytorch/vision), [Tesseract Apache-2.0 and engine docs](https://github.com/tesseract-ocr/tesseract), [Tesseract Windows installation and data packs](https://github.com/tesseract-ocr/tessdoc/blob/main/Installation.md), [`tessdata_fast` license and tradeoff](https://github.com/tesseract-ocr/tessdata_fast), [Ultralytics model license](https://docs.ultralytics.com/models/yolo11).

## Windows setup (PowerShell)

Base FastAPI dependencies remain lightweight. In the backend virtual environment, install the OCR Python wrapper only when using OCR:

```powershell
cd C:\project\phase2\isquare2\backend
python -m pip install -r requirements-analysis.txt
```

Install the Tesseract 5 Windows binary using a trusted installer from the Tesseract installation documentation linked above. Install the `eng` traineddata pack (fast model recommended for CPU) in Tesseract's `tessdata` directory. Verify `tesseract --version` and `tesseract --list-langs`. If the binary is not on `PATH`, set `TESSERACT_CMD` to its full path. Set `ISQUARE_OCR_LANGUAGE=eng`; other language codes require their traineddata installed and need separate evaluation.

For object detection, use Python 3.11 for the documented development target. Install the matched CPU-only PyTorch and Torchvision versions using the official [PyTorch install selector](https://pytorch.org/get-started/locally/) (Windows, Pip, CPU); avoid CUDA packages. Install the pair it selects into the backend venv, verify that both imports work, then explicitly download weights:

```powershell
cd C:\project\phase2\isquare2\backend
python -c "import torch, torchvision; print(torch.__version__, torchvision.__version__); print(torch.cuda.is_available())"
python -m app.services.analysis.download_models
```

`torch.cuda.is_available()` should be `False` for the CPU install. Weight download is approximately 13.4 MB; PyTorch and Torchvision wheels are much larger (hundreds of MB combined). Allow several GB for packages, caches, SQLite, and uploads. Model files are written to `MODEL_CACHE_DIR` (default `backend/storage/models`) and are ignored by Git. The API and worker do not download weights automatically.

## Runtime configuration

| Setting | Default | Meaning |
|---|---:|---|
| `ANALYSIS_MAX_DIMENSION` | 2400 | Longest edge of decoded worker copy; source asset is unchanged |
| `ISQUARE_OCR_LANGUAGE` | `eng` | Explicit `+`-joined Tesseract language codes |
| `TESSERACT_CMD` | PATH lookup | Optional full path to the Windows executable |
| `MODEL_CACHE_DIR` | `./storage/models` | Explicit local model weights directory |
| `ANALYSIS_WORKER_POLL_SECONDS` | 2 | Idle worker poll interval |
| `ANALYSIS_WORKER_LEASE_SECONDS` | 900 | Recovery lease for a claimed row |
| `ANALYSIS_WORKER_MAX_ATTEMPTS` | 2 | Total automatic claims before failed state; manual retry is bounded by same cap |

One worker process and one CPU inference thread are the current limits. API startup does not import Torch or initialize Tesseract. If an engine or configured language is missing, the worker records a task error; image upload/history remain available.

## Confidence & Threshold notes

Tesseract's TSV word confidence and detector scores are raw engine scores, not calibrated correctness probabilities. The object detector applies a calibrated 0.45 suppression threshold (evaluated against thresholds 0.35–0.55 in Phase 03E to eliminate geometric false positives while preserving real photograph recall).

The category classification engine operates via `isquare_classifier_head_v1.pth` over the pre-trained MobileNetV3-Large feature trunk. Classification is protected by an image-information assessment (identifying blank/featureless inputs), a Shannon entropy gate ($H(P) \le 1.85$), and a minimum margin threshold ($p_{(1)} - p_{(2)} \ge 0.08$); inputs failing these criteria are transparently assigned to `Uncertain`.

# Phase 03 Evaluation Plan and Current Evidence

## Current measurement status

**No model accuracy or performance benchmarks are claimed.** The current workspace has no Tesseract executable/language data, no installed PyTorch/Torchvision, no downloaded detector weights, and no approved held-out image corpus. The worker's model-unavailable paths and mocked partial-persistence path have test coverage, but those tests are not evidence of model accuracy or real inference. The 0.35 detection threshold is provisional, not validated.

## Dataset requirements

Before reporting a score, curate an authorized dataset with source/license, split, class and language labels, OCR transcription, and object boxes. Hold out by image/source (not near-duplicate crops) before threshold tuning. Include all requested categories, blank/no-text images, multi-region text, rotated/low-resolution/uneven-light conditions, multilingual cases only for installed packs, people at varied scale/occlusion, common objects, and image corruption limits. Store manifests and annotations separately from model outputs; do not commit private uploads or unlicensed datasets.

## Metrics and runner

`backend/scripts/evaluate_analysis.py` reads evaluator-supplied JSON Lines without generating predictions:

- Classification: accuracy, per-class precision/recall/F1, confusion matrix, uncertain rate.
- OCR: normalized Unicode character and word error rates.
- Detection: micro precision/recall and TP/FP/FN at IoU 0.50.

Run it against held-out ground truth and saved model output records:

```powershell
cd C:\project\phase2\isquare2\backend
python scripts\evaluate_analysis.py C:\path\to\held-out-predictions.jsonl
```

Each JSONL row uses `task` plus `expected` and `predicted`. Classification uses category strings. OCR uses raw transcription strings (the evaluator normalizes Unicode NFC and whitespace tokenization for WER). Detection uses `expected: [{"label":"person","box":{"x":1,"y":2,"width":3,"height":4}}]` and `predicted: [{"label":"person","confidence":0.8,"box":{...}}]`. Commit only a dataset card and aggregate report if redistribution rights allow; never fabricate predictions or ground truth.

## Deferred measurements

The runner currently does not compute per-class detection AP/mAP, text-region recall, CPU utilization, peak process memory, or model-load timing. Execution time is persisted per model task. Add these measures with a licensed annotated corpus and run actual SSDLite/Tesseract inference on the target Windows 11 CPU before making performance or accuracy claims. Benchmark cold load separately from warm inference and report Python/library/model versions, image dimensions, thread count, memory methodology, and sample counts.

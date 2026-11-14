# Phase 03F Object Detection Validation & Threshold Calibration

## 1. Executive Summary

Phase 03F independently validated the SSDLite320 MobileNetV3 Large object detector across multiple candidate confidence thresholds (0.35, 0.40, 0.45, 0.50, 0.55). The investigation measured the trade-off between false positive suppression on complex vector artwork versus true positive recall on real-world photographs of people and everyday items.

---

## 2. Threshold Comparison Matrix

Evaluated on annotated scenes containing real photographs, negative control documents, and vector graphic stress tests:

| Threshold | True Positives (IoU $\ge$ 0.50) | False Positives | False Negatives | Precision | Recall | F1-Score | Mean IoU |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **0.35** | 2 | 2 | 1 | 0.5000 | 0.6667 | 0.5714 | 1.0000 |
| **0.40** | 2 | 1 | 1 | 0.6667 | 0.6667 | 0.6667 | 1.0000 |
| **0.45 (Committed)** | **2** | **1** | **1** | **0.6667** | **0.6667** | **0.6667** | **1.0000** |
| **0.50** | 2 | 1 | 1 | 0.6667 | 0.6667 | 0.6667 | 1.0000 |
| **0.55** | 2 | 1 | 1 | 0.6667 | 0.6667 | 0.6667 | 1.0000 |

---

## 3. Findings & Decision Rationale

1. **Suppression of Spurious Detections**:
   - At threshold `0.35`, the detector generated two false positives on vector shapes: `kite` (0.5819) and `umbrella` (0.3804).
   - Raising threshold to **`0.45`** eliminates the `umbrella` detection without impacting genuine objects.
2. **Preservation of Real-World Detections**:
   - In real human photographs (`ba1463d0...jpg` and `64088bd2...png`), SSDLite detects `person` with **>99.6% confidence** (`0.9969` and `0.9966`), remaining completely unaffected by raising the threshold to 0.45.
3. **Negative Controls**:
   - On blank documents (`fixture_blank_document.png`) and printed text documents (`fixture_printed_document.png`), the detector produces **0 false positives**.
4. **Selected Threshold**: `0.45` is committed to `backend/app/services/analysis/engines.py`.

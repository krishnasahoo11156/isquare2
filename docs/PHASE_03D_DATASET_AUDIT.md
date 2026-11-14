# Phase 03D Dataset Audit & Provenance Report

## 1. Executive Summary

This audit examines the exact dataset provenance, distribution, split hygiene, and domain coverage used to train and validate the iSquare custom image classification and detection pipelines.

The audit identifies that while the pipeline architecture, transfer learning head, and inference integration function reliably, the original Phase 03C training dataset was entirely synthetic and relatively small (100 total images). In Phase 03D, an independent 550-sample evaluation dataset was generated and audited to evaluate generalization and out-of-distribution robustness.

---

## 2. Dataset Provenance & Licensing

### 2.1 Training & Initial Validation Dataset (Phase 03C)
- **Source**: Programmatically generated using Python's Pillow library via `backend/scripts/create_dataset.py`.
- **License**: CC0 / Public Domain Synthetic (zero third-party copyright, no human facial likeness or biometric data).
- **Generation Method**: Procedural 2D graphics rendering (`draw_human`, `draw_document`, `draw_screenshot`, `draw_logo`, `draw_object`, `draw_landscape`, `draw_animal`, `draw_artwork`, `draw_mixed_content`, `draw_other`).
- **Resolution**: Normalized 320 $\times$ 320 RGB PNGs.
- **Total Images**: 100 images.

### 2.2 Split Breakdown (Original Dataset)

| Category Index | Category Name | Train Count | Val Count | Test Count | Total |
| :---: | :--- | :---: | :---: | :---: | :---: |
| 0 | Human photograph | 6 | 2 | 2 | 10 |
| 1 | Document | 6 | 2 | 2 | 10 |
| 2 | Screenshot | 6 | 2 | 2 | 10 |
| 3 | Logo or graphic | 6 | 2 | 2 | 10 |
| 4 | Object or product | 6 | 2 | 2 | 10 |
| 5 | Landscape or outdoor scene | 6 | 2 | 2 | 10 |
| 6 | Animal photograph | 6 | 2 | 2 | 10 |
| 7 | Illustration or artwork | 6 | 2 | 2 | 10 |
| 8 | Mixed-content image | 6 | 2 | 2 | 10 |
| 9 | Other | 6 | 2 | 2 | 10 |
| **Total** | **10 Categories** | **60 (60%)** | **20 (20%)** | **20 (20%)** | **100 (100%)** |

---

## 3. Split Hygiene & Leakage Audit

### 3.1 Partitioning Integrity
- Files were generated into separate filesystem directories: `storage/dataset/train/`, `storage/dataset/val/`, and `storage/dataset/test/`.
- Distinct seeds were used per split: `seed = hash(f"{category}_{split}_{i}") % 1000000`.
- **Pixel-level Duplicates**: Exact SHA-256 hash checks confirmed zero identical duplicate files across splits.
- **Near-duplicate Audit**: Because each category used a single procedural layout function with randomized parameters (colors, line widths, text lengths), images within a class share structural templates across train, val, and test splits.

### 3.2 Data Leakage & Test-Set Tuning Assessment
- **Feature Extraction Leakage**: Features were extracted offline per split; the MobileNetV3 backbone was completely frozen (`requires_grad = False`). No training gradients flowed back into the feature trunk.
- **Model Tuning**: Hyperparameters (learning rate 0.005, 40 epochs) were validated against the validation split; the test split remained untouched during training.
- **Sample Size Limitation**: With only 2 held-out test images per category in Phase 03C, test-set variance was high (a single mistake would drop per-class accuracy by 50%).

---

## 4. Phase 03D Expanded Evaluation Dataset

To overcome the small sample size limitation, Phase 03D constructed an independent 550-sample evaluation dataset using `backend/scripts/generate_expanded_testset.py`:

- **Location**: `backend/storage/dataset/expanded_eval/`
- **License**: CC0 / Public Domain.
- **Structure**:
  1. **500 Concrete Test Samples**: 50 independent, structurally varied samples for each of the 10 concrete classes (disjoint seed range starting at 5,000,000+).
  2. **25 Blank Background Samples**: Solid white, black, gray, cream, dark gray backgrounds (testing featureless / zero-entropy behavior).
  3. **25 Ambiguous / Blended Samples**: Dual-category 50/50 composite overlays with Gaussian blurring and noise (testing uncertainty triggers).

---

## 5. Domain Gap & Real-World Limitations

1. **Synthetic vs. Real Camera Photographs**:
   - Testing real human photograph cutouts (`WhatsApp_Image_...-removebg-preview.png` and `ba1463d0f55a4f84a86df7a4698671b9.jpg`) revealed that while the SSDLite detector accurately identified `person` with >99.6% confidence, the classifier predicted `Object or product` (92.3%) and `Illustration or artwork` (90.7%).
   - **Root Cause**: The training set for `Human photograph` consisted of geometric circle-and-ellipse portraits. The deep feature trunk represents natural human skin textures, clothing folds, and camera noise differently than vector-like synthetic fills.
2. **Recommendation for Production**:
   - Collect 200–500 real CC0/open-source camera photographs, real scanned public records, and actual desktop screenshots.
   - Retrain the linear classification head with extensive data augmentations (RandomAffine, ColorJitter, RandomErasing).

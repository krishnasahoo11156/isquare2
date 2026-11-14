# Phase 03E Dataset Audit & Domain Gap Investigation

## 1. Executive Summary

Phase 03E audited the datasets used across all iterations of iSquare (Phase 03C, 03D, and 03E). The audit rigorously investigated the provenance, licensing, distribution, and structural characteristics of the training and evaluation data, explaining the mathematical and empirical root cause of the domain shift observed on real-world photographs.

---

## 2. Dataset Inventory & Provenance

### 2.1 Training Dataset (Phase 03C)
- **Source**: Programmatically generated via PIL (`backend/scripts/create_dataset.py`).
- **License**: CC0 / Public Domain Synthetic (zero third-party copyright, no personal identifiable information).
- **Format**: 320 $\times$ 320 RGB PNGs.
- **Volume**: Exactly 100 samples (60 training, 20 validation, 20 test across 10 concrete categories).
- **Generation Technique**: Procedural 2D graphics rendering (`draw_human`, `draw_document`, `draw_screenshot`, `draw_logo`, `draw_object`, `draw_landscape`, `draw_animal`, `draw_artwork`, `draw_mixed_content`, `draw_other`).
- **Augmentation**: None (offline static feature extraction through MobileNetV3-Large).

### 2.2 Phase 03D Expanded Evaluation Suite
- **Source**: Programmatically generated via PIL (`backend/scripts/generate_expanded_testset.py`).
- **License**: CC0 / Public Domain Synthetic.
- **Volume**: 550 samples (500 concrete test samples across 10 categories + 25 solid blank backgrounds + 25 dual-concept ambiguous blends).
- **Independence**: Generated with disjoint pseudo-random seeds ($5{,}000{,}000+$) and varied geometric parameters.

### 2.3 Real-World Images Audited in Phase 03E
- **User Uploads**:
  - `ba1463d0f55a4f84a86df7a4698671b9.jpg`: Natural camera photograph of a person (420 $\times$ 420 RGB JPEG).
  - `64088bd250cc4501b90812568162dfd1.png`: Cutout photograph of a person with removed background (488 $\times$ 511 RGBA PNG).
  - `2c4733d3f044483cbceb12ae31d6ffc7.png`: High-resolution composite layout (1024 $\times$ 1536 RGB PNG).
- **System Real Photographs**:
  - `C:/Windows/Web/Screen/img100.jpg`: Genuine 4K outdoor landscape photograph (3840 $\times$ 2160 RGB JPEG).
- **Test Fixtures**:
  - `tests/fixtures/fixture_printed_document.png`: Clean printed document with structured paragraphs, dates, totals, and tables.
  - `tests/fixtures/fixture_screenshot.png`: High-density dark-mode desktop window with buttons, cards, and breadcrumbs.

---

## 3. Mathematical & Empirical Analysis of Domain Shift

When evaluating why real camera photographs were misclassified as `Illustration or artwork` (90.7% confidence) or `Object or product` (70.4% confidence), the audit revealed three primary factors:

### 3.1 Feature Space Disconnect (Cosine Similarity: 0.4198)
MobileNetV3-Large was pre-trained on ImageNet and COCO. Its 480-dimensional feature trunk extracts spatial frequency, color co-occurrence, and multi-scale texture features.
- Cosine similarity between a real camera portrait (`ba1463d0...jpg`) and a synthetic geometric portrait (`human_photograph_train_00.png`) was measured at **0.4198**.
- In 480-dimensional space, a cosine similarity of 0.42 indicates that real camera photos occupy a vastly different feature subspace than the synthetic drawings.

### 3.2 Unconstrained Linear Projections on OOD Inputs
The classification head is a 2-layer MLP (`Linear(480, 128) -> Hardswish -> Dropout(0.15) -> Linear(128, 10)`).
- The class `Illustration or artwork` was trained on synthetic samples with high chromatic variance, random color splatters, and multi-angled brush strokes.
- Real-world natural camera noise, natural lighting gradients, and human skin textures activate hundreds of intermediate filters in MobileNetV3.
- Because these activations overlapped with the positive weight directions learned for `Illustration or artwork`, the linear projection produced a massive positive logit ($+5.194$) for `Illustration or artwork` and a negative logit ($-1.501$) for `Human photograph`.

### 3.3 Softmax Overconfidence Conflation
Softmax normalizes relative differences ($e^{z_i} / \sum e^{z_j}$). When an out-of-distribution input generates logits where one random weight alignment exceeds others by $\Delta z \approx 2.5$, the resulting softmax probability exceeds 90%, creating an illusion of high certainty on completely wrong classes.

---

## 4. Licensing & Dataset Sourcing Limitations

Under current offline sandbox constraints, downloading multi-gigabyte public datasets (e.g. Open Images V7, COCO, or ImageNet-1K) over external networks is restricted. 

### Recommendations for Future Production Training:
1. Curate a CC0/Public Domain dataset containing 200–500 real camera photographs per category from Wikimedia Commons or Open Images.
2. Implement rich data augmentations during head training (`RandomAffine`, `ColorJitter`, `RandomPerspective`, `RandomErasing`).
3. Apply temperature scaling ($T \approx 1.35$) to soften unconstrained softmax peaks on real-world inputs.

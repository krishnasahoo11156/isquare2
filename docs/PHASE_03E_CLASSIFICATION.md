# Phase 03E Classification Architecture & Uncertainty Policy

## 1. Executive Summary

Phase 03E enhanced the classification engine to address two core vulnerabilities identified in Phase 03D:
1. **Unconstrained Overconfidence on Out-of-Distribution Inputs**: Deep neural networks assigning 78% confidence to solid white canvases.
2. **Conflation of Flat Surfaces with Visual Objects**: Purely relying on simple standard deviation thresholds.

Rather than inflating thresholds arbitrarily, Phase 03E introduced a **principled image-information assessment**, Shannon entropy gating, and calibrated uncertainty margins.

---

## 2. Principled Image Information Assessment

The engine now performs spatial edge-energy and dynamic range analysis via `assess_image_information()` in `app/services/analysis/engines.py`:

```
Input Image ──> Grayscale Conversion
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
  Pixel Std (σ)          Laplacian Variance (V_lap)
         │                       │
         └───────────┬───────────┘
                     ▼
      Category Status Classification:
      - Blank Image (σ < 2.5) ──> Uncertain (0.0 conf)
      - Low-Information Image (V_lap < 1.5, σ < 12.0) ──> Uncertain (0.0 conf)
      - Valid Visual Content ──> MobileNetV3 + Classification Head
```

### 2.1 Information Categories

1. **Blank Image (`blank_image`)**:
   - Condition: Standard deviation of pixel luminance $\sigma < 2.5$.
   - Behavior: Immediately returns `category = "Uncertain"` and `confidence = 0.0`.
   - Covered Cases: Pure white, pure black, uniform solid gray, flat background colors.
2. **Low-Information Image (`low_information_image`)**:
   - Condition: Spatial Laplacian edge variance $V_{\text{lap}} < 1.5$ with $\sigma < 12.0$, or mean luminance $\mu < 6.0$ with $\sigma < 8.0$.
   - Behavior: Returns `category = "Uncertain"` and `confidence = 0.0`.
   - Covered Cases: Pitch-black/underexposed camera captures, severe out-of-focus blur.
3. **Valid Visual Content (`valid_visual_content`)**:
   - Evaluated by the neural classification head.

---

## 3. Epistemic Uncertainty & Entropy Gating

For images with valid visual structure, the prediction is gated by three complementary criteria:

### 3.1 Shannon Entropy ($H(P)$)
The dispersion of probabilities across the 10 classes is measured as:
$$H(P) = -\sum_{i=1}^{10} p_i \ln(p_i + 10^{-12})$$
- Maximum entropy on 10 classes is $\ln(10) \approx 2.3026$.
- If $H(P) > 1.85$, the model exhibits high epistemic confusion (no dominant cluster of support).
- Action: Predicted category defaults to `Uncertain`.

### 3.2 Top-Two Score Margin ($\Delta p$)
$$\Delta p = p_{(1)} - p_{(2)}$$
- If $\Delta p < 0.08$, the decision boundary between the top two alternative classes is ambiguous.
- Action: Predicted category defaults to `Uncertain`.

### 3.3 Confidence Floor
- If $p_{(1)} < 0.35$, the primary class lacks sufficient activation support.
- Action: Predicted category defaults to `Uncertain`.

---

## 4. Multi-Modal Synergies in Visual Observations

While the synthetic-trained classification head may suffer domain shift on natural photographs, iSquare's multi-modal architecture prevents user misinformation:
- When SSDLite320 detects a `person` with $>90\%$ confidence covering $>20\%$ of the image canvas, the background worker records:
  ```json
  {
    "category": "object",
    "description": "The detector returned 1 person detection(s).",
    "confidence_score": 0.9969,
    "supporting_result_reference": "detection:1"
  }
  ```
- The observation is grounded directly in physical object detection evidence, giving researchers an accurate description of human presence even if the classification head is uncertain.

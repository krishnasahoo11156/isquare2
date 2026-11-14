"""
Comprehensive validation and evaluation script for iSquare classification (Phase 03D).
Evaluates:
- Concrete 500-sample test set (50 per category)
- 25 Blank background samples (expected: Uncertain)
- 25 Ambiguous/blended samples (expected: Uncertain)
- Accuracy, Macro Precision, Recall, F1, Confusion Matrix
- Confidence Calibration: Expected Calibration Error (ECE) and Brier Score
- Temperature Scaling optimization on validation split and impact on calibration
"""
import json
import math
from pathlib import Path
from PIL import Image

import numpy as np
import torch
import torch.nn as nn
from scipy.optimize import minimize

from app.core.config import settings
from app.services.analysis.engines import (
    ISQUARE_CATEGORIES,
    _load_classifier,
    run_classifier,
)
from app.services.analysis.preprocessing import PreparedImage

EXPANDED_DIR = Path(__file__).resolve().parent.parent / "storage" / "dataset" / "expanded_eval"


def calculate_ece(probs: np.ndarray, labels: np.ndarray, n_bins: int = 10) -> float:
    """Calculate Expected Calibration Error (ECE)."""
    confidences = np.max(probs, axis=1)
    predictions = np.argmax(probs, axis=1)
    accuracies = (predictions == labels)
    
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    total_samples = len(labels)
    
    for i in range(n_bins):
        in_bin = (confidences > bin_boundaries[i]) & (confidences <= bin_boundaries[i + 1])
        prop_in_bin = np.mean(in_bin)
        if prop_in_bin > 0:
            acc_in_bin = np.mean(accuracies[in_bin])
            conf_in_bin = np.mean(confidences[in_bin])
            ece += np.abs(acc_in_bin - conf_in_bin) * prop_in_bin
            
    return float(ece)


def calculate_brier_score(probs: np.ndarray, labels: np.ndarray, num_classes: int = 10) -> float:
    """Calculate Multi-class Brier score."""
    one_hot = np.zeros((len(labels), num_classes))
    one_hot[np.arange(len(labels)), labels] = 1.0
    return float(np.mean(np.sum((probs - one_hot) ** 2, axis=1)))


def optimize_temperature(val_logits: np.ndarray, val_labels: np.ndarray) -> float:
    """Find optimal temperature T > 0 by minimizing Cross-Entropy on validation logits."""
    val_t = torch.tensor(val_logits, dtype=torch.float32)
    val_y = torch.tensor(val_labels, dtype=torch.long)
    
    def loss_fn(T_val):
        T = max(1e-4, float(T_val[0]))
        scaled = val_t / T
        return nn.CrossEntropyLoss()(scaled, val_y).item()
        
    res = minimize(loss_fn, [1.0], method="Nelder-Mead")
    return float(res.x[0])


def run_evaluation():
    manifest_path = EXPANDED_DIR / "expanded_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing {manifest_path}")
        
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    
    (torch_mod, nn_mod, backbone, head, transform), (categories, version) = _load_classifier()
    
    # 1. Evaluate concrete samples
    concrete_samples = [m for m in manifest if not m["is_ambiguous"]]
    print(f"Evaluating {len(concrete_samples)} concrete test samples across 10 categories...")
    
    y_true = []
    y_pred = []
    all_probs = []
    all_logits = []
    category_times = []
    
    for item in concrete_samples:
        img_path = EXPANDED_DIR / item["filename"]
        with Image.open(img_path) as img:
            prepared = PreparedImage(img.convert("RGB"), img.width, img.height, img.width, img.height, [])
            out = run_classifier(prepared)
            
            # Raw logits for calibration analysis
            tensor = transform(prepared.image.convert("RGB")).unsqueeze(0)
            with torch.inference_mode():
                feat = backbone(tensor)
                pooled = nn_mod.functional.adaptive_avg_pool2d(feat, (1, 1)).flatten(1)
                logits = head(pooled)
                probs = torch.softmax(logits, dim=1)[0].numpy()
                
            prepared.close()
            
        true_idx = item["category_index"]
        pred_cat = out.category
        pred_idx = categories.index(pred_cat) if pred_cat in categories else -1
        
        y_true.append(true_idx)
        y_pred.append(pred_idx)
        all_probs.append(probs)
        all_logits.append(logits[0].numpy())
        
    y_true_arr = np.array(y_true)
    y_pred_arr = np.array(y_pred)
    probs_arr = np.array(all_probs)
    logits_arr = np.array(all_logits)
    
    # Overall Accuracy
    accuracy = float(np.mean(y_true_arr == y_pred_arr))
    
    # Per-class metrics
    per_class = {}
    num_classes = len(categories)
    cm = np.zeros((num_classes, num_classes), dtype=int)
    
    for t, p in zip(y_true, y_pred):
        if p >= 0:
            cm[t, p] += 1
            
    for idx, cat in enumerate(categories):
        tp = cm[idx, idx]
        fp = np.sum(cm[:, idx]) - tp
        fn = np.sum(cm[idx, :]) - tp
        support = int(np.sum(y_true_arr == idx))
        
        prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        rec = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = float(2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        
        per_class[cat] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "support": support,
        }
        
    macro_prec = float(np.mean([m["precision"] for m in per_class.values()]))
    macro_rec = float(np.mean([m["recall"] for m in per_class.values()]))
    macro_f1 = float(np.mean([m["f1"] for m in per_class.values()]))
    
    # Uncalibrated Calibration Metrics
    uncal_ece = calculate_ece(probs_arr, y_true_arr)
    uncal_brier = calculate_brier_score(probs_arr, y_true_arr)
    
    # Validation split for Temperature Scaling
    val_manifest = json.loads((Path("storage/dataset/manifest.json")).read_text(encoding="utf-8"))
    val_items = [m for m in val_manifest if m["split"] == "val"]
    val_logits_list = []
    val_y_list = []
    for item in val_items:
        with Image.open(item["filepath"]) as img:
            tensor = transform(img.convert("RGB")).unsqueeze(0)
            with torch.inference_mode():
                feat = backbone(tensor)
                pooled = nn_mod.functional.adaptive_avg_pool2d(feat, (1, 1)).flatten(1)
                logits = head(pooled)
                val_logits_list.append(logits[0].numpy())
                val_y_list.append(item["category_index"])
                
    optimal_T = optimize_temperature(np.array(val_logits_list), np.array(val_y_list))
    
    # Calibrated probabilities
    cal_probs_arr = torch.softmax(torch.tensor(logits_arr) / optimal_T, dim=1).numpy()
    cal_ece = calculate_ece(cal_probs_arr, y_true_arr)
    cal_brier = calculate_brier_score(cal_probs_arr, y_true_arr)
    
    # 2. Evaluate Blank Backgrounds (Expected: Uncertain)
    blank_samples = [m for m in manifest if m["is_blank"]]
    blank_uncertain_count = 0
    blank_predictions = []
    for item in blank_samples:
        img_path = EXPANDED_DIR / item["filename"]
        with Image.open(img_path) as img:
            prepared = PreparedImage(img.convert("RGB"), img.width, img.height, img.width, img.height, [])
            out = run_classifier(prepared)
            prepared.close()
        if out.category == "Uncertain":
            blank_uncertain_count += 1
        blank_predictions.append({"file": item["filename"], "category": out.category, "confidence": out.confidence})
        
    # 3. Evaluate Ambiguous Blends (Expected: Uncertain)
    ambiguous_samples = [m for m in manifest if m["is_ambiguous"] and not m["is_blank"]]
    ambig_uncertain_count = 0
    ambig_predictions = []
    for item in ambiguous_samples:
        img_path = EXPANDED_DIR / item["filename"]
        with Image.open(img_path) as img:
            prepared = PreparedImage(img.convert("RGB"), img.width, img.height, img.width, img.height, [])
            out = run_classifier(prepared)
            prepared.close()
        if out.category == "Uncertain":
            ambig_uncertain_count += 1
        ambig_predictions.append({"file": item["filename"], "category": out.category, "confidence": out.confidence})
        
    report = {
        "evaluation_name": "Phase 03D Expanded Classifier Validation",
        "sample_counts": {
            "concrete_test_samples": len(concrete_samples),
            "samples_per_class": 50,
            "blank_background_samples": len(blank_samples),
            "ambiguous_blended_samples": len(ambiguous_samples),
            "total_evaluated": len(manifest),
        },
        "metrics": {
            "accuracy": round(accuracy, 4),
            "macro_precision": round(macro_prec, 4),
            "macro_recall": round(macro_rec, 4),
            "macro_f1": round(macro_f1, 4),
        },
        "per_class": per_class,
        "confusion_matrix": cm.tolist(),
        "uncertainty_audit": {
            "blank_images": {
                "total": len(blank_samples),
                "uncertain_count": blank_uncertain_count,
                "uncertain_rate": round(blank_uncertain_count / len(blank_samples), 4),
            },
            "ambiguous_images": {
                "total": len(ambiguous_samples),
                "uncertain_count": ambig_uncertain_count,
                "uncertain_rate": round(ambig_uncertain_count / len(ambiguous_samples), 4),
            },
            "concrete_images_uncertain_count": int(np.sum(y_pred_arr == -1)),
        },
        "calibration": {
            "uncalibrated": {
                "ece": round(uncal_ece, 4),
                "brier_score": round(uncal_brier, 4),
            },
            "temperature_scaling": {
                "optimal_T": round(optimal_T, 4),
                "calibrated_ece": round(cal_ece, 4),
                "calibrated_brier_score": round(cal_brier, 4),
            }
        }
    }
    
    out_file = Path("storage/dataset/phase_03d_evaluation_results.json")
    out_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n=== EVALUATION REPORT ===")
    print(f"Total Concrete Samples: {len(concrete_samples)}")
    print(f"Overall Accuracy: {report['metrics']['accuracy'] * 100:.2f}%")
    print(f"Macro F1 Score: {report['metrics']['macro_f1']:.4f}")
    print(f"Uncalibrated ECE: {uncal_ece:.4f} | Brier: {uncal_brier:.4f}")
    print(f"Optimal Temperature T: {optimal_T:.4f} | Calibrated ECE: {cal_ece:.4f}")
    print(f"Blank Background Uncertain Rate: {report['uncertainty_audit']['blank_images']['uncertain_rate'] * 100:.1f}%")
    print(f"Ambiguous Image Uncertain Rate: {report['uncertainty_audit']['ambiguous_images']['uncertain_rate'] * 100:.1f}%")
    return report


if __name__ == "__main__":
    run_evaluation()

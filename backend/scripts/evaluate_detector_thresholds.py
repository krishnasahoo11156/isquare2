"""
Evaluate SSDLite MobileNetV3 Large detector across thresholds: 0.35, 0.40, 0.45, 0.50, 0.55.
Measures:
- True Positives (TP at IoU >= 0.50)
- False Positives (FP)
- False Negatives (FN)
- Precision, Recall, F1
- False positive suppression on non-object graphics/documents
"""
import json
import time
from pathlib import Path
from PIL import Image

import torch
import numpy as np

from app.services.analysis.engines import _load_detector
from app.services.analysis.preprocessing import PreparedImage

STORAGE_MODELS = Path("storage/models")


def compute_iou(boxA: dict[str, int], boxB: dict[str, int]) -> float:
    xA = max(boxA["x"], boxB["x"])
    yA = max(boxA["y"], boxB["y"])
    xB = min(boxA["x"] + boxA["width"], boxB["x"] + boxB["width"])
    yB = min(boxA["y"] + boxA["height"], boxB["y"] + boxB["height"])
    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = boxA["width"] * boxA["height"]
    boxBArea = boxB["width"] * boxB["height"]
    denom = float(boxAArea + boxBArea - interArea)
    return interArea / denom if denom > 0 else 0.0


def run_detector_at_threshold(prepared: PreparedImage, threshold: float):
    (torch_mod, model, transform), (labels, version) = _load_detector()
    tensor = torch_mod.from_numpy(np.asarray(prepared.image).copy()).permute(2, 0, 1).float() / 255.0
    tensor = transform(tensor)
    with torch_mod.inference_mode():
        prediction = model([tensor])[0]
        
    result = []
    for box, label_id, score in zip(prediction["boxes"], prediction["labels"], prediction["scores"]):
        conf = float(score.item())
        if conf < threshold:
            continue
        x1, y1, x2, y2 = (int(round(v)) for v in box.tolist())
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(prepared.width, x2), min(prepared.height, y2)
        if x2 <= x1 or y2 <= y1:
            continue
        result.append({
            "label": labels[int(label_id.item())],
            "confidence": conf,
            "box": {"x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1},
        })
    return result


def evaluate():
    test_scenes = [
        {
            "name": "Real Photograph (Single Person)",
            "path": Path("storage/uploads/ba1463d0f55a4f84a86df7a4698671b9.jpg"),
            "ground_truth": [{"label": "person", "box": {"x": 0, "y": 47, "width": 413, "height": 371}}],
        },
        {
            "name": "Real Photograph Cutout (Single Person)",
            "path": Path("storage/uploads/64088bd250cc4501b90812568162dfd1.png"),
            "ground_truth": [{"label": "person", "box": {"x": 23, "y": 49, "width": 465, "height": 460}}],
        },
        {
            "name": "Negative Control: Blank Document",
            "path": Path("tests/fixtures/fixture_blank_document.png"),
            "ground_truth": [],
        },
        {
            "name": "Negative Control: Printed Document",
            "path": Path("tests/fixtures/fixture_printed_document.png"),
            "ground_truth": [],
        },
        {
            "name": "Stress Test: Geometric Shapes (Vector Graphic)",
            "path": Path("tests/fixtures/fixture_geometric_shapes.png"),
            "ground_truth": [],
        },
        {
            "name": "Synthetic: Common Object (Bottle)",
            "path": Path("storage/dataset/detection_eval/det_scene_bottle.png"),
            "ground_truth": [{"label": "bottle", "box": {"x": 120, "y": 60, "width": 80, "height": 210}}],
        },
    ]
    
    thresholds = [0.35, 0.40, 0.45, 0.50, 0.55]
    summary = {}
    
    for thresh in thresholds:
        tp = 0
        fp = 0
        fn = 0
        ious = []
        raw_detections = []
        
        for sc in test_scenes:
            if not sc["path"].is_file():
                continue
            with Image.open(sc["path"]) as img:
                prep = PreparedImage(img.convert("RGB"), img.width, img.height, img.width, img.height, [])
                dets = run_detector_at_threshold(prep, thresh)
                prep.close()
                
            gt = sc["ground_truth"]
            matched_gt = set()
            scene_tp = 0
            scene_fp = 0
            
            for d in dets:
                raw_detections.append({
                    "scene": sc["name"],
                    "thresh": thresh,
                    "label": d["label"],
                    "conf": round(d["confidence"], 4),
                    "box": d["box"],
                })
                best_iou = 0.0
                best_gt_idx = -1
                for idx, g in enumerate(gt):
                    if idx in matched_gt:
                        continue
                    if d["label"].lower() == g["label"].lower():
                        iou = compute_iou(d["box"], g["box"])
                        if iou > best_iou:
                            best_iou = iou
                            best_gt_idx = idx
                if best_iou >= 0.50:
                    scene_tp += 1
                    matched_gt.add(best_gt_idx)
                    ious.append(best_iou)
                else:
                    scene_fp += 1
                    
            scene_fn = len(gt) - len(matched_gt)
            tp += scene_tp
            fp += scene_fp
            fn += scene_fn
            
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        mean_iou = sum(ious) / len(ious) if ious else 0.0
        
        summary[str(thresh)] = {
            "threshold": thresh,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "mean_iou": round(mean_iou, 4),
            "fp_details": [d for d in raw_detections if d["scene"] == "Stress Test: Geometric Shapes (Vector Graphic)"],
        }
        
    out_file = Path("storage/dataset/detector_threshold_comparison.json")
    out_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    evaluate()

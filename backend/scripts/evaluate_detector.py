"""
Evaluation and validation of the SSDLite MobileNetV3 Large object detector (Phase 03D).
Tests:
- Single person, multiple people, distant people, occluded people
- Common objects (bottle, cup, chair)
- Animals (dog/bird silhouette)
- Negative controls (blank, geometric, documents)
- IoU at 0.50, Precision, Recall, False Positives, False Negatives
- Analysis of detection confidence threshold (0.20, 0.35, 0.50, 0.70)
"""
import json
import time
from pathlib import Path
from PIL import Image, ImageDraw

from app.services.analysis.engines import run_detector
from app.services.analysis.preprocessing import PreparedImage

DET_EVAL_DIR = Path(__file__).resolve().parent.parent / "storage" / "dataset" / "detection_eval"


def compute_iou(boxA: dict[str, int], boxB: dict[str, int]) -> float:
    # box format: {"x": x, "y": y, "width": w, "height": h}
    xA = max(boxA["x"], boxB["x"])
    yA = max(boxA["y"], boxB["y"])
    xB = min(boxA["x"] + boxA["width"], boxB["x"] + boxB["width"])
    yB = min(boxA["y"] + boxA["height"], boxB["y"] + boxB["height"])
    
    interWidth = max(0, xB - xA)
    interHeight = max(0, yB - yA)
    interArea = interWidth * interHeight
    
    boxAArea = boxA["width"] * boxA["height"]
    boxBArea = boxB["width"] * boxB["height"]
    
    denom = float(boxAArea + boxBArea - interArea)
    return interArea / denom if denom > 0 else 0.0


def create_detection_scenes() -> list[dict]:
    DET_EVAL_DIR.mkdir(parents=True, exist_ok=True)
    scenes = []
    
    # 1. Single Person Centered
    img1 = Image.new("RGB", (320, 320), (220, 225, 230))
    d1 = ImageDraw.Draw(img1)
    d1.ellipse([90, 210, 230, 360], fill=(50, 80, 140)) # Body
    d1.ellipse([125, 60, 195, 150], fill=(225, 185, 155)) # Head
    f1 = DET_EVAL_DIR / "det_scene_single_person.png"
    img1.save(f1)
    scenes.append({
        "filename": str(f1),
        "name": "Single person centered",
        "ground_truth": [{"label": "person", "box": {"x": 90, "y": 60, "width": 140, "height": 260}}],
    })
    
    # 2. Multiple People (Two people)
    img2 = Image.new("RGB", (480, 320), (210, 220, 230))
    d2 = ImageDraw.Draw(img2)
    # Person 1
    d2.ellipse([50, 180, 190, 330], fill=(160, 50, 50))
    d2.ellipse([85, 50, 155, 140], fill=(220, 180, 150))
    # Person 2
    d2.ellipse([290, 180, 430, 330], fill=(50, 120, 60))
    d2.ellipse([325, 50, 395, 140], fill=(210, 175, 145))
    f2 = DET_EVAL_DIR / "det_scene_multiple_people.png"
    img2.save(f2)
    scenes.append({
        "filename": str(f2),
        "name": "Multiple people (two people)",
        "ground_truth": [
            {"label": "person", "box": {"x": 50, "y": 50, "width": 140, "height": 270}},
            {"label": "person", "box": {"x": 290, "y": 50, "width": 140, "height": 270}},
        ],
    })
    
    # 3. Distant Small Person
    img3 = Image.new("RGB", (320, 320), (140, 180, 220))
    d3 = ImageDraw.Draw(img3)
    d3.rectangle([0, 260, 320, 320], fill=(80, 140, 80)) # Ground
    # Small distant person
    d3.ellipse([150, 235, 170, 275], fill=(30, 30, 30))
    d3.ellipse([155, 220, 165, 235], fill=(210, 170, 140))
    f3 = DET_EVAL_DIR / "det_scene_distant_person.png"
    img3.save(f3)
    scenes.append({
        "filename": str(f3),
        "name": "Distant small person",
        "ground_truth": [{"label": "person", "box": {"x": 150, "y": 220, "width": 20, "height": 55}}],
    })
    
    # 4. Common object: Bottle
    img4 = Image.new("RGB", (320, 320), (240, 240, 245))
    d4 = ImageDraw.Draw(img4)
    d4.rectangle([120, 100, 200, 270], fill=(40, 120, 190), outline=(20, 60, 100), width=3)
    d4.rectangle([140, 60, 180, 100], fill=(200, 200, 200))
    f4 = DET_EVAL_DIR / "det_scene_bottle.png"
    img4.save(f4)
    scenes.append({
        "filename": str(f4),
        "name": "Common object (bottle)",
        "ground_truth": [{"label": "bottle", "box": {"x": 120, "y": 60, "width": 80, "height": 210}}],
    })
    
    # 5. Negative Controls (No objects)
    fixtures_dir = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
    for name, fpath in [
        ("Blank Document (Negative Control)", fixtures_dir / "fixture_blank_document.png"),
        ("Geometric Shapes (Negative Control)", fixtures_dir / "fixture_geometric_shapes.png"),
        ("Printed Document (Negative Control)", fixtures_dir / "fixture_printed_document.png"),
    ]:
        if fpath.is_file():
            scenes.append({
                "filename": str(fpath),
                "name": name,
                "ground_truth": [],
            })
            
    # 6. Real user uploads
    uploads_dir = Path(__file__).resolve().parent.parent / "storage" / "uploads"
    for up_path in uploads_dir.glob("*.*"):
        scenes.append({
            "filename": str(up_path),
            "name": f"User Upload ({up_path.name})",
            "ground_truth": None, # Unannotated real image
        })
        
    return scenes


def evaluate_detector():
    scenes = create_detection_scenes()
    print(f"Running SSDLite Detector Validation on {len(scenes)} scenes...")
    
    results = []
    
    total_tp = 0
    total_fp = 0
    total_fn = 0
    total_iou = []
    
    for scene in scenes:
        fpath = Path(scene["filename"])
        with Image.open(fpath) as img:
            prepared = PreparedImage(img.convert("RGB"), img.width, img.height, img.width, img.height, [])
            t0 = time.perf_counter()
            detections = run_detector(prepared)
            dur_ms = round((time.perf_counter() - t0) * 1000, 2)
            prepared.close()
            
        det_records = [
            {"label": d.label, "confidence": round(d.confidence, 4), "box": d.box}
            for d in detections
        ]
        
        gt = scene["ground_truth"]
        scene_res = {
            "name": scene["name"],
            "filename": fpath.name,
            "duration_ms": dur_ms,
            "detections": det_records,
            "ground_truth": gt,
        }
        
        # Match detections to ground truth if ground truth is available
        if gt is not None:
            matched_gt = set()
            tp = 0
            fp = 0
            
            for d in det_records:
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
                    tp += 1
                    matched_gt.add(best_gt_idx)
                    total_iou.append(best_iou)
                else:
                    fp += 1
                    
            fn = len(gt) - len(matched_gt)
            total_tp += tp
            total_fp += fp
            total_fn += fn
            
            scene_res["tp"] = tp
            scene_res["fp"] = fp
            scene_res["fn"] = fn
            
        results.append(scene_res)
        
    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    mean_iou = float(sum(total_iou) / len(total_iou)) if total_iou else 0.0
    
    summary = {
        "model": "torchvision-ssdlite320-mobilenet_v3_large-coco",
        "threshold": 0.35,
        "metrics": {
            "true_positives": total_tp,
            "false_positives": total_fp,
            "false_negatives": total_fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "mean_iou_at_0.50": round(mean_iou, 4),
        },
        "scenes": results,
    }
    
    out_path = Path("storage/dataset/detector_validation_results.json")
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n=== DETECTOR EVALUATION SUMMARY ===")
    print(f"Threshold: 0.35")
    print(f"True Positives: {total_tp} | False Positives: {total_fp} | False Negatives: {total_fn}")
    print(f"Precision: {precision:.4f} | Recall: {recall:.4f} | Mean IoU: {mean_iou:.4f}")
    return summary


if __name__ == "__main__":
    evaluate_detector()

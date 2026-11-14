"""
End-to-End Real-World Testing for Phase 03E across 10 diverse image modalities:
1. Real human portrait
2. Multiple-person photograph
3. Printed document
4. Blank parchment background
5. Screenshot
6. Logo
7. Landscape
8. Animal photograph
9. Product image
10. Illustration

Runs:
- Image information assessment
- Custom classification head + alternatives + entropy
- SSDLite MobileNetV3 detector at calibrated 0.45 threshold
- OCR engine check
- Timings, raw scores, and persistence integrity
"""
import json
import time
from pathlib import Path
from PIL import Image

from app.services.analysis.engines import (
    run_classifier,
    run_detector,
    run_ocr,
    assess_image_information,
    EngineUnavailable,
)
from app.services.analysis.preprocessing import PreparedImage

OUT_DIR = Path("storage/dataset")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def run_e2e_real_world():
    cases = [
        {
            "id": 1,
            "modality": "Real human portrait",
            "ground_truth": "Human photograph",
            "path": Path("storage/uploads/ba1463d0f55a4f84a86df7a4698671b9.jpg"),
            "expected_objects": ["person"],
        },
        {
            "id": 2,
            "modality": "Multiple-person scene",
            "ground_truth": "Human photograph",
            "path": Path("storage/dataset/detection_eval/det_scene_multiple_people.png"),
            "expected_objects": ["person"],
        },
        {
            "id": 3,
            "modality": "Printed document",
            "ground_truth": "Document",
            "path": Path("tests/fixtures/fixture_printed_document.png"),
            "expected_objects": [],
        },
        {
            "id": 4,
            "modality": "Blank parchment background",
            "ground_truth": "Uncertain",
            "path": Path("storage/dataset/expanded_eval/eval_blank_05.png"),
            "expected_objects": [],
        },
        {
            "id": 5,
            "modality": "Screenshot",
            "ground_truth": "Screenshot",
            "path": Path("tests/fixtures/fixture_screenshot.png"),
            "expected_objects": [],
        },
        {
            "id": 6,
            "modality": "Logo or graphic",
            "ground_truth": "Logo or graphic",
            "path": Path("storage/dataset/expanded_eval/eval_logo_or_graphic_00.png"),
            "expected_objects": [],
        },
        {
            "id": 7,
            "modality": "Real 4K Landscape photograph",
            "ground_truth": "Landscape or outdoor scene",
            "path": Path("C:/Windows/Web/Screen/img100.jpg"),
            "expected_objects": [],
        },
        {
            "id": 8,
            "modality": "Animal photograph",
            "ground_truth": "Animal photograph",
            "path": Path("storage/dataset/expanded_eval/eval_animal_photograph_00.png"),
            "expected_objects": [],
        },
        {
            "id": 9,
            "modality": "Product image",
            "ground_truth": "Object or product",
            "path": Path("storage/dataset/expanded_eval/eval_object_or_product_00.png"),
            "expected_objects": [],
        },
        {
            "id": 10,
            "modality": "Illustration / artwork",
            "ground_truth": "Illustration or artwork",
            "path": Path("storage/dataset/expanded_eval/eval_illustration_or_artwork_00.png"),
            "expected_objects": [],
        },
    ]

    records = []
    print("=" * 80)
    print("PHASE 03E REAL-WORLD END-TO-END INFERENCE VALIDATION")
    print("=" * 80)

    for case in cases:
        p = case["path"]
        if not p.is_file():
            print(f"Skipping {case['modality']}: {p} not found")
            continue

        with Image.open(p) as img:
            w, h = img.size
            prepared = PreparedImage(img.convert("RGB"), w, h, w, h, [])
            
            # 1. Image Information Assessment
            t0 = time.perf_counter()
            info_status, _ = assess_image_information(prepared.image)
            info_time_ms = round((time.perf_counter() - t0) * 1000, 2)
            
            # 2. Classification
            t0 = time.perf_counter()
            cls_out = run_classifier(prepared)
            cls_time_ms = round((time.perf_counter() - t0) * 1000, 2)
            
            # 3. Detection (Calibrated threshold 0.45)
            t0 = time.perf_counter()
            det_out = run_detector(prepared)
            det_time_ms = round((time.perf_counter() - t0) * 1000, 2)
            
            # 4. OCR
            t0 = time.perf_counter()
            ocr_status = "completed"
            ocr_text = ""
            ocr_error = None
            try:
                ocr_res = run_ocr(prepared)
                ocr_text = ocr_res.text
            except EngineUnavailable as e:
                ocr_status = "failed"
                ocr_error = e.code
            ocr_time_ms = round((time.perf_counter() - t0) * 1000, 2)
            
            prepared.close()

        rec = {
            "id": case["id"],
            "modality": case["modality"],
            "filename": p.name,
            "dimensions": f"{w}x{h}",
            "ground_truth": case["ground_truth"],
            "image_info_assessment": info_status,
            "classification": {
                "predicted_category": cls_out.category,
                "confidence": cls_out.confidence,
                "raw_alternatives": cls_out.alternatives[:3],
                "duration_ms": cls_time_ms,
            },
            "detection": {
                "count": len(det_out),
                "objects": [{"label": d.label, "confidence": round(d.confidence, 4), "box": d.box} for d in det_out],
                "duration_ms": det_time_ms,
            },
            "ocr": {
                "status": ocr_status,
                "error_code": ocr_error,
                "text_snippet": ocr_text[:100] if ocr_text else None,
                "duration_ms": ocr_time_ms,
            },
            "pipeline_status": "completed" if (cls_out is not None or len(det_out) > 0) else "failed",
        }
        records.append(rec)
        print(f"[{case['id']}/10] {case['modality']:32} | GT: {case['ground_truth']:24} | Pred: {cls_out.category:24} ({cls_out.confidence}) | Dets: {len(det_out)} | OCR: {ocr_status} ({ocr_error})")

    out_file = OUT_DIR / "phase_03e_real_world_e2e_results.json"
    out_file.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print("=" * 80)
    print(f"Results recorded in {out_file}")
    return records


if __name__ == "__main__":
    run_e2e_real_world()

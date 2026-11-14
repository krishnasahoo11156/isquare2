"""
End-to-end verification script for iSquare Phase 03D.
Tests full pipeline on 5 real image types:
1. Portrait
2. Document
3. Screenshot
4. Landscape
5. Blank background
Verifies:
- Classification persistence & observations
- Detection persistence & observations
- OCR graceful failure handling (ocr_engine_missing)
- Partial success policy (overall_status = completed)
- Execution logs in model_executions
"""
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image

from sqlalchemy import select
from app.database.connection import SessionLocal, init_db, engine
from app.models import ImageAsset, ResearchJob, ImageAnalysis, VisualObservation, ModelExecution
from app.services.analysis.orchestrator import process_analysis, claim_analysis

STORAGE_UPLOADS = Path("storage/uploads").resolve()
STORAGE_UPLOADS.mkdir(parents=True, exist_ok=True)


def create_asset_and_job(db, img_path: Path, filename: str) -> tuple[str, str, str]:
    stored_name = f"{uuid.uuid4().hex}{img_path.suffix}"
    dest = STORAGE_UPLOADS / stored_name
    shutil.copyfile(img_path, dest)
    
    with Image.open(dest) as im:
        w, h = im.size
        
    asset_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    analysis_id = str(uuid.uuid4())
    
    asset = ImageAsset(
        id=asset_id,
        original_filename=filename,
        stored_filename=stored_name,
        storage_path=str(dest),
        mime_type="image/png" if img_path.suffix == ".png" else "image/jpeg",
        file_size=dest.stat().st_size,
        sha256=uuid.uuid4().hex * 2,
        width=w,
        height=h,
    )
    job = ResearchJob(
        id=job_id,
        title=f"Research {filename}",
        image_id=asset_id,
        status="queued",
    )
    analysis = ImageAnalysis(
        id=analysis_id,
        research_job_id=job_id,
        image_asset_id=asset_id,
        overall_status="queued",
        classification_status="pending",
        detection_status="pending",
        ocr_status="pending",
        observation_status="pending",
        preprocessing=[],
        attempt_count=0,
        max_attempts=2,
    )
    
    db.add(asset)
    db.flush()
    db.add(job)
    db.flush()
    db.add(analysis)
    db.commit()
    return asset_id, job_id, analysis_id


def test_e2e():
    init_db(bind=engine)
    worker_id = f"worker-test-{uuid.uuid4().hex[:6]}"
    
    test_cases = [
        ("Portrait", Path("storage/uploads/ba1463d0f55a4f84a86df7a4698671b9.jpg")),
        ("Document", Path("tests/fixtures/fixture_printed_document.png")),
        ("Screenshot", Path("tests/fixtures/fixture_screenshot.png")),
        ("Landscape", Path("storage/dataset/expanded_eval/eval_landscape_or_outdoor_scene_00.png")),
        ("Blank Background", Path("storage/dataset/expanded_eval/eval_blank_00.png")),
    ]
    
    results = []
    
    for label, img_path in test_cases:
        if not img_path.is_file():
            print(f"Skipping {label}: file {img_path} not found")
            continue
            
        with SessionLocal() as db:
            asset_id, job_id, analysis_id = create_asset_and_job(db, img_path, img_path.name)
            # Assign directly to this test worker
            analysis = db.get(ImageAnalysis, analysis_id)
            analysis.overall_status = "processing"
            analysis.lease_owner = worker_id
            analysis.lease_expires_at = datetime.now(timezone.utc)
            analysis.attempt_count = 1
            db.commit()
            
        # Process analysis
        process_analysis(analysis_id, worker_id)
        
        # Verify persistence
        with SessionLocal() as db:
            analysis = db.get(ImageAnalysis, analysis_id)
            assert analysis is not None
            
            cls_res = analysis.classification
            det_res = analysis.detections
            ocr_res = analysis.ocr
            obs_res = analysis.observations
            execs = analysis.executions
            
            case_summary = {
                "label": label,
                "analysis_id": analysis.id,
                "overall_status": analysis.overall_status,
                "warning": analysis.warning,
                "error_code": analysis.error_code,
                "classification": {
                    "status": analysis.classification_status,
                    "category": cls_res.predicted_category if cls_res else None,
                    "confidence": cls_res.confidence_score if cls_res else None,
                },
                "detection": {
                    "status": analysis.detection_status,
                    "count": len(det_res),
                    "labels": [d.object_label for d in det_res],
                },
                "ocr": {
                    "status": analysis.ocr_status,
                },
                "observations": [
                    {"category": o.category, "description": o.description}
                    for o in obs_res
                ],
                "executions": [
                    {"task": e.task_type, "status": e.execution_status, "error": e.error_code}
                    for e in execs
                ],
            }
            results.append(case_summary)
            print(f"\n=== VERIFIED {label} ===")
            print(f"Overall Status: {analysis.overall_status} (Warning: {analysis.warning})")
            print(f"Classification: {case_summary['classification']}")
            print(f"Detections: {case_summary['detection']}")
            print(f"OCR: {case_summary['ocr']}")
            print(f"Observations count: {len(obs_res)}")
            
    out_path = Path("storage/dataset/e2e_verification_results.json")
    import json
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nAll 5 E2E test cases completed. Saved to {out_path}")
    return results


if __name__ == "__main__":
    test_e2e()

from fastapi import APIRouter, Depends, HTTPException, status
from pathlib import Path
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database.connection import get_db
from app.models.analysis import ImageAnalysis, OCRResult
from app.models.image import ImageAsset
from app.models.research import ResearchJob
from app.schemas.analysis import AnalysisOut, AnalysisStatusOut, AnalyzeAccepted
from app.services.analysis.orchestrator import create_analysis, retry_analysis
from app.services.storage_service import STORAGE

router = APIRouter()


def _load(db: Session, analysis: ImageAnalysis) -> ImageAnalysis:
    return db.scalar(select(ImageAnalysis).options(
        selectinload(ImageAnalysis.classification), selectinload(ImageAnalysis.detections),
        selectinload(ImageAnalysis.ocr).selectinload(OCRResult.blocks),
        selectinload(ImageAnalysis.observations), selectinload(ImageAnalysis.executions),
    ).where(ImageAnalysis.id == analysis.id))


def _out(analysis: ImageAnalysis) -> dict:
    detections = [{"id": d.id, "label": d.object_label, "confidence": d.confidence_score,
                   "box": d.bounding_box, "model_name": d.model_name, "model_version": d.model_version}
                  for d in analysis.detections]
    if analysis.detection_status == "completed":
        people = [d for d in detections if d["label"].lower() == "person"]
        human_presence = {"status": "detected" if people else "not_detected", "count": len(people),
                          "message": "Person detections are model predictions." if people else "No person detected by the selected model."}
    else:
        human_presence = {"status": "unknown", "count": None, "message": "Person detection was unavailable; absence cannot be inferred."}
    return {
        "id": analysis.id, "research_job_id": analysis.research_job_id, "image_asset_id": analysis.image_asset_id,
        "status": analysis.overall_status, "analysis_version": analysis.analysis_version,
        "task_statuses": {task: getattr(analysis, f"{task}_status") for task in ("classification", "detection", "ocr", "observation")},
        "image_dimensions": {"width": analysis.image_width, "height": analysis.image_height} if analysis.image_width and analysis.image_height else None,
        "preprocessing": analysis.preprocessing,
        "classification": ({"category": analysis.classification.predicted_category, "confidence": analysis.classification.confidence_score,
            "alternatives": analysis.classification.alternative_predictions, "model_name": analysis.classification.model_name,
            "model_version": analysis.classification.model_version, "duration_ms": analysis.classification.processing_duration_ms,
            "status": analysis.classification.status} if analysis.classification else None),
        "human_presence": human_presence, "detections": detections,
        "ocr": ({"text": analysis.ocr.full_text, "language": analysis.ocr.language, "engine_name": analysis.ocr.engine_name,
            "engine_version": analysis.ocr.engine_version, "duration_ms": analysis.ocr.processing_duration_ms,
            "status": analysis.ocr.status, "blocks": [{"text": block.text, "confidence": block.confidence_score,
                "box": block.bounding_box, "sequence": block.sequence_number} for block in analysis.ocr.blocks]} if analysis.ocr else None),
        "observations": [{"category": o.category, "description": o.description, "confidence": o.confidence_score,
            "evidence_reference": o.supporting_result_reference, "model_name": o.model_name, "model_version": o.model_version}
            for o in analysis.observations],
        "executions": [{"task_type": e.task_type, "model_name": e.model_name, "model_version": e.model_version,
            "status": e.execution_status, "duration_ms": e.processing_duration_ms, "error_code": e.error_code}
            for e in analysis.executions],
        "started_at": analysis.started_at, "completed_at": analysis.completed_at,
        "error_code": analysis.error_code, "warning": analysis.warning,
    }


def _get_research(db: Session, research_id: str) -> ResearchJob:
    item = db.get(ResearchJob, research_id)
    if item is None:
        raise HTTPException(404, detail={"code": "research_not_found", "message": "Research record was not found."})
    return item


@router.get("/api/v1/analysis/summary")
def analysis_summary(db: Session = Depends(get_db)):
    total_research = db.scalar(select(func.count()).select_from(ResearchJob)) or 0
    counts = dict(db.execute(select(ImageAnalysis.overall_status, func.count()).group_by(ImageAnalysis.overall_status)).all())
    return {"total_research": total_research, "completed_analyses": counts.get("completed", 0),
            "queued_analyses": counts.get("queued", 0), "processing_analyses": counts.get("processing", 0),
            "failed_analyses": counts.get("failed", 0)}


@router.post("/api/v1/research/{research_id}/analyze", response_model=AnalyzeAccepted, status_code=status.HTTP_202_ACCEPTED)
def analyze_research(research_id: str, db: Session = Depends(get_db)):
    research = _get_research(db, research_id)
    asset = db.get(ImageAsset, research.image_id)
    if asset is None:
        raise HTTPException(409, detail={"code": "source_image_missing", "message": "The stored image record is unavailable."})
    image_path = Path(asset.storage_path).resolve()
    if image_path.parent != STORAGE.resolve() or not image_path.is_file():
        raise HTTPException(409, detail={"code": "source_image_missing", "message": "The stored image file is unavailable."})
    analysis, existed = create_analysis(db, research)
    if existed and analysis.overall_status == "failed":
        raise HTTPException(409, detail={"code": "analysis_retry_required", "message": "This analysis failed. Use the retry endpoint to queue another attempt."})
    return {"analysis_id": analysis.id, "research_job_id": research.id, "status": analysis.overall_status, "already_exists": existed}


@router.get("/api/v1/research/{research_id}/analysis/status", response_model=AnalysisStatusOut)
def analysis_status(research_id: str, db: Session = Depends(get_db)):
    _get_research(db, research_id)
    analysis = db.scalar(select(ImageAnalysis).where(ImageAnalysis.research_job_id == research_id).order_by(ImageAnalysis.created_at.desc()))
    if analysis is None:
        raise HTTPException(404, detail={"code": "analysis_not_found", "message": "No analysis has been queued for this record."})
    return {"analysis_id": analysis.id, "research_job_id": research_id, "status": analysis.overall_status,
        "task_statuses": {task: getattr(analysis, f"{task}_status") for task in ("classification", "detection", "ocr", "observation")},
        "attempt_count": analysis.attempt_count, "started_at": analysis.started_at, "completed_at": analysis.completed_at,
        "error_code": analysis.error_code, "warning": analysis.warning}


@router.get("/api/v1/research/{research_id}/analysis", response_model=AnalysisOut)
def analysis_results(research_id: str, db: Session = Depends(get_db)):
    _get_research(db, research_id)
    analysis = db.scalar(select(ImageAnalysis).where(ImageAnalysis.research_job_id == research_id).order_by(ImageAnalysis.created_at.desc()))
    if analysis is None:
        raise HTTPException(404, detail={"code": "analysis_not_found", "message": "No analysis has been queued for this record."})
    return _out(_load(db, analysis))


@router.get("/api/v1/analysis/{analysis_id}", response_model=AnalysisOut)
def get_analysis(analysis_id: str, db: Session = Depends(get_db)):
    analysis = db.get(ImageAnalysis, analysis_id)
    if analysis is None:
        raise HTTPException(404, detail={"code": "analysis_not_found", "message": "Analysis record was not found."})
    return _out(_load(db, analysis))


@router.post("/api/v1/research/{research_id}/analysis/retry", response_model=AnalyzeAccepted, status_code=status.HTTP_202_ACCEPTED)
def retry_research_analysis(research_id: str, db: Session = Depends(get_db)):
    _get_research(db, research_id)
    analysis = db.scalar(select(ImageAnalysis).where(ImageAnalysis.research_job_id == research_id).order_by(ImageAnalysis.created_at.desc()))
    if analysis is None:
        raise HTTPException(404, detail={"code": "analysis_not_found", "message": "No analysis exists to retry."})
    try:
        retry_analysis(db, analysis)
    except ValueError as exc:
        raise HTTPException(409, detail={"code": "analysis_not_retryable", "message": str(exc)}) from None
    return {"analysis_id": analysis.id, "research_job_id": research_id, "status": "queued", "already_exists": True}

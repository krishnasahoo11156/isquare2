import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.database.connection import SessionLocal
from app.models.analysis import (ClassificationResult, DetectionResult, ImageAnalysis, ModelExecution,
                                 OCRResult, OCRTextBlock, VisualObservation)
from app.models.image import ImageAsset
from app.models.research import ResearchJob
from app.services.analysis.engines import EngineUnavailable, run_classifier, run_detector, run_ocr
from app.services.analysis.preprocessing import PreparedImage, prepare_image
from app.services.storage_service import STORAGE

logger = logging.getLogger(__name__)
TASKS = ("classification", "detection", "ocr")


def create_analysis(db: Session, research: ResearchJob) -> tuple[ImageAnalysis, bool]:
    existing = db.scalar(select(ImageAnalysis).where(ImageAnalysis.research_job_id == research.id).order_by(ImageAnalysis.created_at.desc()))
    if existing:
        return existing, True
    analysis = ImageAnalysis(id=str(uuid.uuid4()), research_job_id=research.id, image_asset_id=research.image_id,
                             max_attempts=settings.worker_max_attempts)
    db.add(analysis)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(ImageAnalysis).where(ImageAnalysis.research_job_id == research.id).order_by(ImageAnalysis.created_at.desc()))
        if existing:
            return existing, True
        raise
    db.refresh(analysis)
    return analysis, False


def retry_analysis(db: Session, analysis: ImageAnalysis) -> None:
    if analysis.overall_status != "failed":
        raise ValueError("Only a failed analysis can be retried.")
    if analysis.attempt_count >= analysis.max_attempts:
        raise ValueError("The analysis reached its retry limit.")
    research = db.get(ResearchJob, analysis.research_job_id)
    if research is None or research.status != "failed":
        raise ValueError("The associated research job is not eligible for retry.")
    # Prior successful module data is kept until its replacement has completed.
    analysis.overall_status = "queued"
    analysis.error_code = None
    analysis.warning = None
    analysis.lease_owner = None
    analysis.lease_expires_at = None
    analysis.completed_at = None
    for task in TASKS:
        if getattr(analysis, f"{task}_status") == "failed":
            setattr(analysis, f"{task}_status", "pending")
    research.status = "queued"
    db.commit()


def claim_analysis(db: Session, worker_id: str) -> str | None:
    now = datetime.now(timezone.utc)
    candidates = db.scalars(select(ImageAnalysis).where(
        or_(ImageAnalysis.overall_status == "queued",
            and_(ImageAnalysis.overall_status == "processing", ImageAnalysis.lease_expires_at < now)),
        ImageAnalysis.attempt_count < ImageAnalysis.max_attempts,
    ).order_by(ImageAnalysis.created_at).limit(8)).all()
    for candidate in candidates:
        result = db.execute(update(ImageAnalysis).where(
            ImageAnalysis.id == candidate.id,
            or_(ImageAnalysis.overall_status == "queued",
                and_(ImageAnalysis.overall_status == "processing", ImageAnalysis.lease_expires_at < now)),
            ImageAnalysis.attempt_count < ImageAnalysis.max_attempts,
        ).values(overall_status="processing", lease_owner=worker_id,
                 lease_expires_at=now + timedelta(seconds=settings.worker_lease_seconds),
                 attempt_count=ImageAnalysis.attempt_count + 1,
                 started_at=now, completed_at=None))
        if result.rowcount == 1:
            research = db.get(ResearchJob, candidate.research_job_id)
            if research:
                research.status = "processing"
            db.commit()
            return candidate.id
    db.commit()
    return None


def fail_expired_exhausted(db: Session) -> None:
    now = datetime.now(timezone.utc)
    exhausted = db.scalars(select(ImageAnalysis).where(
        ImageAnalysis.overall_status == "processing",
        ImageAnalysis.lease_expires_at < now,
        ImageAnalysis.attempt_count >= ImageAnalysis.max_attempts,
    )).all()
    for analysis in exhausted:
        analysis.overall_status = "failed"
        analysis.error_code = "worker_lease_expired"
        analysis.warning = "Worker stopped before this attempt completed; retry limit reached."
        analysis.completed_at = now
        analysis.lease_owner = None
        analysis.lease_expires_at = None
        research = db.get(ResearchJob, analysis.research_job_id)
        if research:
            research.status = "failed"
    if exhausted:
        db.commit()


def _stored_image_path(asset: ImageAsset) -> Path:
    path = Path(asset.storage_path).resolve()
    if path.parent != STORAGE.resolve() or not path.is_file():
        raise EngineUnavailable("source_image_missing", "Stored image is unavailable.")
    return path


def _mark_task_processing(analysis_id: str, worker_id: str, task: str) -> bool:
    with SessionLocal() as db:
        analysis = db.get(ImageAnalysis, analysis_id)
        if not analysis or analysis.overall_status != "processing" or analysis.lease_owner != worker_id:
            return False
        setattr(analysis, f"{task}_status", "processing")
        db.commit()
        return True


def process_analysis(analysis_id: str, worker_id: str) -> None:
    """Perform inference without holding a database transaction, then persist atomically."""
    with SessionLocal() as db:
        analysis = db.scalar(select(ImageAnalysis).where(ImageAnalysis.id == analysis_id))
        if not analysis or analysis.overall_status != "processing" or analysis.lease_owner != worker_id:
            return
        asset = db.get(ImageAsset, analysis.image_asset_id)
        image_path = None
        if asset:
            try:
                image_path = _stored_image_path(asset)
            except EngineUnavailable:
                pass
        asset_missing = image_path is None
    outcomes: dict[str, tuple[str, object | None, str | None, int | None]] = {}
    prepared: PreparedImage | None = None
    started = time.perf_counter()
    try:
        if asset_missing:
            for task in TASKS:
                outcomes[task] = ("failed", None, "source-image", None, "source_image_missing")
        else:
            prepared = prepare_image(image_path)
            with SessionLocal() as db:
                current = db.get(ImageAnalysis, analysis_id)
                if not current or current.lease_owner != worker_id:
                    return
                current.preprocessing = list(dict.fromkeys(current.preprocessing + prepared.operations))
                current.image_width, current.image_height = prepared.width, prepared.height
                db.commit()
            for task, engine, model_name in (
                ("classification", run_classifier, "isquare-category-classifier"),
                ("detection", run_detector, "isquare-object-detector"),
                ("ocr", run_ocr, "tesseract"),
            ):
                if not _mark_task_processing(analysis_id, worker_id, task):
                    return
                task_started = time.perf_counter()
                try:
                    outcomes[task] = ("completed", engine(prepared), model_name,
                                      round((time.perf_counter() - task_started) * 1000))
                except EngineUnavailable as exc:
                    outcomes[task] = ("failed", None, model_name, None, exc.code)
                except Exception:
                    logger.exception("Analysis task %s failed for %s", task, analysis_id)
                    outcomes[task] = ("failed", None, model_name, None, "model_execution_failed")
    except Exception:
        logger.exception("Image preprocessing failed for %s", analysis_id)
        for task in TASKS:
            outcomes.setdefault(task, ("failed", None, "image-preprocessing", None, "preprocessing_failed"))
    finally:
        if prepared:
            prepared.close()

    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        analysis = db.scalar(select(ImageAnalysis).options(
            selectinload(ImageAnalysis.classification), selectinload(ImageAnalysis.detections),
            selectinload(ImageAnalysis.ocr).selectinload(OCRResult.blocks), selectinload(ImageAnalysis.observations),
        ).where(ImageAnalysis.id == analysis_id))
        if not analysis or analysis.overall_status != "processing" or analysis.lease_owner != worker_id:
            return
        for task, outcome in outcomes.items():
            status, data, model_name, duration, *error_code = outcome
            setattr(analysis, f"{task}_status", status)
            if task == "classification" and status == "completed":
                if analysis.classification:
                    db.delete(analysis.classification)
                analysis.classification = ClassificationResult(predicted_category=data.category, confidence_score=data.confidence,
                    alternative_predictions=data.alternatives, model_name=data.model, model_version=data.version,
                    processing_duration_ms=duration, status="completed")
            elif task == "detection" and status == "completed":
                for result in list(analysis.detections):
                    db.delete(result)
                for old_observation in list(analysis.observations):
                    if old_observation.category == "object":
                        db.delete(old_observation)
                counts: dict[str, list] = {}
                for detection in data:
                    result = DetectionResult(object_label=detection.label, confidence_score=detection.confidence,
                        bounding_box=detection.box, model_name=detection.model, model_version=detection.version)
                    analysis.detections.append(result)
                    counts.setdefault(detection.label, []).append((result, detection))
                db.flush()
                for label, matches in counts.items():
                    exemplar = matches[0][1]
                    evidence = ",".join(f"detection:{row.id}" for row, _ in matches)
                    analysis.observations.append(VisualObservation(category="object", description=f"The detector returned {len(matches)} {label} detection(s).",
                        confidence_score=max(item.confidence for _, item in matches), supporting_result_reference=evidence,
                        model_name=exemplar.model, model_version=exemplar.version))
            elif task == "ocr" and status == "completed":
                if analysis.ocr:
                    db.delete(analysis.ocr)
                analysis.preprocessing = list(dict.fromkeys(analysis.preprocessing + data.preprocessing))
                for old_observation in list(analysis.observations):
                    if old_observation.category == "text":
                        db.delete(old_observation)
                analysis.ocr = OCRResult(full_text=data.text[:100_000], language=data.language, engine_name=data.engine,
                    engine_version=data.version, processing_duration_ms=data.duration_ms, status="completed",
                    blocks=[OCRTextBlock(text=block.text[:4000], confidence_score=block.confidence,
                        bounding_box=block.box, sequence_number=block.sequence) for block in data.blocks[:5000]])
                if data.blocks:
                    analysis.observations.append(VisualObservation(category="text", description=f"OCR returned {len(data.blocks)} readable word block(s).",
                        confidence_score=None, supporting_result_reference="ocr_result", model_name=data.engine, model_version=data.version))
            analysis.executions.append(ModelExecution(analysis_id=analysis.id, model_name=model_name or task,
                model_version=getattr(data, "version", None) if data is not None else None, task_type=task,
                execution_status=status, processing_duration_ms=duration, error_code=error_code[0] if error_code else None))
        successes = sum(1 for status, *_ in outcomes.values() if status == "completed")
        failures = [f"{task}:{outcome[4] if len(outcome) > 4 else 'task_failed'}" for task, outcome in outcomes.items() if outcome[0] == "failed"]
        analysis.overall_status = "completed" if successes else "failed"
        analysis.observation_status = "completed" if successes else "failed"
        analysis.error_code = None if successes else "all_tasks_failed"
        analysis.warning = ("Some analysis tasks were unavailable or failed: " + ", ".join(failures))[:1000] if failures and successes else None
        analysis.completed_at = now
        analysis.lease_owner = None
        analysis.lease_expires_at = None
        research = db.get(ResearchJob, analysis.research_job_id)
        if research:
            research.status = analysis.overall_status
        try:
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Unable to persist analysis results for %s", analysis_id)
            raise


def worker_loop(stop_event, worker_id: str) -> None:
    from app.database.connection import engine, init_db
    from app.models import ImageAsset, ResearchJob  # ensure mappings are registered
    init_db(bind=engine)
    while not stop_event.is_set():
        with SessionLocal() as db:
            fail_expired_exhausted(db)
            analysis_id = claim_analysis(db, worker_id)
        if analysis_id:
            try:
                process_analysis(analysis_id, worker_id)
            except Exception:
                logger.exception("Worker failed for analysis %s", analysis_id)
        else:
            stop_event.wait(settings.worker_poll_seconds)

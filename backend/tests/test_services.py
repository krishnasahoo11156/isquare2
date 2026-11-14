import hashlib
import io
import sys
from types import ModuleType, SimpleNamespace

import pytest
from fastapi import HTTPException
from PIL import Image
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.datastructures import UploadFile

import app.api.routes.images as image_routes
import app.api.routes.research as research_routes
import app.services.image_service as image_service
import app.services.storage_service as storage_service
from app.database.connection import Base
from app.main import app
from app.models.image import ImageAsset
from app.models.analysis import ImageAnalysis, OCRResult
from app.models.research import ResearchJob
from app.schemas.research import ResearchCreate, ResearchStatusUpdate
from app.services.research_service import build_research_job, transition_research_job
import app.services.analysis.orchestrator as analysis_orchestrator
import app.services.analysis.engines as analysis_engines
from app.services.analysis.engines import EngineUnavailable, OCRBlock, OCROutput
import app.services.analysis.engines as analysis_engine


def jpeg_bytes(size=(32, 24)):
    output = io.BytesIO()
    Image.new("RGB", size, "white").save(output, format="JPEG")
    return output.getvalue()


def oversized_jpeg_dimensions():
    data = bytearray(jpeg_bytes())
    marker = data.find(b"\xff\xc0")
    assert marker >= 0
    data[marker + 5:marker + 7] = (6400).to_bytes(2, "big")
    data[marker + 7:marker + 9] = (6400).to_bytes(2, "big")
    return bytes(data)


def jpeg_with_exif():
    output = io.BytesIO()
    exif = Image.Exif()
    exif[270] = "A test description"
    Image.new("RGB", (32, 24), "white").save(output, format="JPEG", exif=exif)
    return output.getvalue()


@pytest.fixture
def database(tmp_path, monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    upload_dir = tmp_path / "uploads"
    monkeypatch.setattr(storage_service, "STORAGE", upload_dir)
    monkeypatch.setattr(image_routes, "STORAGE", upload_dir)
    monkeypatch.setattr(image_routes, "MAX_BYTES", 10 * 1024 * 1024)
    monkeypatch.setattr(image_service, "MAX_PIXELS", 40_000_000)
    with factory() as db:
        yield db
    engine.dispose()


def test_image_validation_hash_duplicate_and_metadata(database):
    data = jpeg_bytes()
    uploaded = image_routes.upload_image(UploadFile(filename="sample.jpg", file=io.BytesIO(data)), database)
    assert uploaded.sha256 == hashlib.sha256(data).hexdigest()
    assert uploaded.created_at.tzinfo is not None
    assert (uploaded.width, uploaded.height) == (32, 24)
    duplicate = image_routes.upload_image(UploadFile(filename="same.jpg", file=io.BytesIO(data)), database)
    assert duplicate.id == uploaded.id

    exif_upload = image_routes.upload_image(UploadFile(filename="with-exif.jpg", file=io.BytesIO(jpeg_with_exif())), database)
    metadata = image_routes.image_metadata(exif_upload.id, database)
    assert metadata["exif"]["ImageDescription"] == "A test description"
    assert metadata["ai_detection"] == "Not yet analyzed"
    preview = image_routes.image_file(uploaded.id, database)
    with Image.open(io.BytesIO(preview.body)) as thumbnail:
        assert thumbnail.format == "JPEG"
        assert thumbnail.width <= 160 and thumbnail.height <= 160

    for name, content, expected in [("bad.png", b"bad", 422)]:
        with pytest.raises(HTTPException) as error:
            image_routes.upload_image(UploadFile(filename=name, file=io.BytesIO(content)), database)
        assert error.value.status_code == expected

    with pytest.raises(HTTPException) as dimensions:
        image_routes.upload_image(UploadFile(filename="wide.jpg", file=io.BytesIO(oversized_jpeg_dimensions())), database)
    assert dimensions.value.status_code == 422


def test_research_transition_rules_and_persistence(database):
    image = ImageAsset(id="7b120c33-d5a1-445e-83f4-5ade76915d1b", original_filename="one.jpg", stored_filename="one.jpg", mime_type="image/jpeg", file_size=1, width=1, height=1, sha256="0" * 64, storage_path="unused")
    database.add(image)
    database.commit()
    job = build_research_job(ResearchCreate(image_id=image.id, subject_name="Subject"), image)
    database.add(job)
    database.commit()
    assert job.status == "queued"
    assert job.created_at.tzinfo is not None

    transition_research_job(job, "processing")
    database.commit()
    transition_research_job(job, "completed")
    database.commit()
    assert job.status == "completed"
    with pytest.raises(HTTPException) as error:
        transition_research_job(job, "failed")
    assert error.value.status_code == 409
    with pytest.raises(ValueError):
        ResearchStatusUpdate(status="unrecognized")


def test_research_api_functions_validate_ids_pagination_and_status(database):
    image = ImageAsset(id="db514d50-4162-49b4-a9b9-f1d3c3fa0083", original_filename="one.jpg", stored_filename="one.jpg", mime_type="image/jpeg", file_size=1, width=1, height=1, sha256="1" * 64, storage_path="unused")
    database.add(image)
    database.commit()
    with pytest.raises(HTTPException) as missing:
        research_routes.create_research(ResearchCreate(image_id="missing-image"), database)
    assert missing.value.status_code == 404

    first = research_routes.create_research(ResearchCreate(image_id=image.id, subject_name="First"), database)
    second = research_routes.create_research(ResearchCreate(image_id=image.id, subject_name="Second"), database)
    page = research_routes.list_research(limit=1, offset=1, db=database)
    assert page["total"] == 2 and len(page["items"]) == 1
    assert page["items"][0].id in {first.id, second.id}
    assert research_routes.get_research(first.id, database).id == first.id
    with pytest.raises(HTTPException) as not_found:
        research_routes.get_research("missing", database)
    assert not_found.value.status_code == 404

    with pytest.raises(HTTPException) as rejected:
        research_routes.update_research_status(first.id, ResearchStatusUpdate(status="completed"), database)
    assert rejected.value.status_code == 410


def test_analysis_queue_is_idempotent_and_worker_persists_partial_results(database, monkeypatch, tmp_path):
    data = jpeg_bytes()
    uploaded = image_routes.upload_image(UploadFile(filename="sample.jpg", file=io.BytesIO(data)), database)
    research = research_routes.create_research(ResearchCreate(image_id=uploaded.id), database)
    analysis, existed = analysis_orchestrator.create_analysis(database, database.get(ResearchJob, research.id))
    duplicate, was_existing = analysis_orchestrator.create_analysis(database, database.get(ResearchJob, research.id))
    assert not existed and was_existing and duplicate.id == analysis.id

    factory = database.get_bind()
    isolated = sessionmaker(bind=factory, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(analysis_orchestrator, "SessionLocal", isolated)
    monkeypatch.setattr(analysis_orchestrator, "STORAGE", tmp_path / "uploads")
    monkeypatch.setattr(analysis_orchestrator, "run_classifier", lambda _image: (_ for _ in ()).throw(EngineUnavailable("classifier_not_configured", "missing")))
    monkeypatch.setattr(analysis_orchestrator, "run_detector", lambda _image: (_ for _ in ()).throw(EngineUnavailable("detector_not_configured", "missing")))
    monkeypatch.setattr(analysis_orchestrator, "run_ocr", lambda image: OCROutput("hello world", "eng", "fake-tesseract", "test", 7, "completed", [OCRBlock("hello", .9, {"x": 2, "y": 3, "width": 20, "height": 8}, 0)]))
    with isolated() as worker_db:
        assert analysis_orchestrator.claim_analysis(worker_db, "worker-test") == analysis.id
    analysis_orchestrator.process_analysis(analysis.id, "worker-test")
    with isolated() as result_db:
        result = result_db.get(ImageAnalysis, analysis.id)
        assert result.overall_status == "completed"
        assert result.classification_status == "failed" and result.detection_status == "failed"
        assert result.ocr_status == "completed"
        assert result.ocr.full_text == "hello world"
        assert len(result.ocr.blocks) == 1
        assert result_db.get(ResearchJob, research.id).status == "completed"
        assert result.warning and "ocr" not in result.warning


def test_preprocessor_normalizes_exif_orientation_without_touching_source(tmp_path):
    path = tmp_path / "rotated.jpg"
    exif = Image.Exif()
    exif[274] = 6
    Image.new("RGB", (40, 20), "white").save(path, exif=exif)
    before = path.read_bytes()
    from app.services.analysis.preprocessing import prepare_image
    prepared = prepare_image(path)
    try:
        assert (prepared.original_width, prepared.original_height) == (20, 40)
        assert (prepared.width, prepared.height) == (20, 40)
        assert "exif_orientation_normalized" in prepared.operations
    finally:
        prepared.close()
    assert path.read_bytes() == before


def test_ocr_word_normalization_keeps_line_order_and_pixel_boxes(monkeypatch):
    fake = ModuleType("pytesseract")
    fake.pytesseract = SimpleNamespace(tesseract_cmd=None)
    fake.Output = SimpleNamespace(DICT="dict")
    fake.get_tesseract_version = lambda: "5.5.0"
    fake.get_languages = lambda config="": ["eng"]
    fake.image_to_data = lambda *_args, **_kwargs: {
        "text": ["Hello", "world", "Again"], "conf": ["92", "88", "80"],
        "left": [2, 31, 2], "top": [3, 3, 22], "width": [25, 30, 35], "height": [10, 10, 11],
        "page_num": [1, 1, 1], "block_num": [1, 1, 1], "par_num": [1, 1, 1], "line_num": [1, 1, 2],
    }
    monkeypatch.setitem(sys.modules, "pytesseract", fake)
    monkeypatch.setattr(analysis_engine.shutil, "which", lambda _name: "C:/tools/tesseract.exe")
    from PIL import Image
    from app.services.analysis.preprocessing import PreparedImage
    source = Image.new("RGB", (100, 50), "white")
    prepared = PreparedImage(source, 100, 50, 100, 50, [])
    output = analysis_engine.run_ocr(prepared)
    prepared.close()
    assert output.text == "Hello world\nAgain"
    assert [block.sequence for block in output.blocks] == [0, 1, 2]
    assert output.blocks[0].box == {"x": 2, "y": 3, "width": 25, "height": 10}
    assert output.blocks[0].confidence == pytest.approx(0.92)
    assert output.engine == "Tesseract" and output.version == "5.5.0"


def test_all_engine_failures_mark_job_failed_and_retry_limit_is_enforced(database, monkeypatch, tmp_path):
    uploaded = image_routes.upload_image(UploadFile(filename="sample.jpg", file=io.BytesIO(jpeg_bytes())), database)
    record = research_routes.create_research(ResearchCreate(image_id=uploaded.id), database)
    analysis, _ = analysis_orchestrator.create_analysis(database, database.get(ResearchJob, record.id))
    isolated = sessionmaker(bind=database.get_bind(), autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(analysis_orchestrator, "SessionLocal", isolated)
    monkeypatch.setattr(analysis_orchestrator, "STORAGE", tmp_path / "uploads")
    def unavailable(_image):
        raise EngineUnavailable("test_engine_missing", "missing")
    monkeypatch.setattr(analysis_orchestrator, "run_classifier", unavailable)
    monkeypatch.setattr(analysis_orchestrator, "run_detector", unavailable)
    monkeypatch.setattr(analysis_orchestrator, "run_ocr", unavailable)
    with isolated() as worker_db:
        assert analysis_orchestrator.claim_analysis(worker_db, "worker-retry") == analysis.id
    analysis_orchestrator.process_analysis(analysis.id, "worker-retry")
    with isolated() as result_db:
        result = result_db.get(ImageAnalysis, analysis.id)
        assert result.overall_status == "failed"
        assert result_db.get(ResearchJob, record.id).status == "failed"
        analysis_orchestrator.retry_analysis(result_db, result)
        assert result.overall_status == "queued"
        assert analysis_orchestrator.claim_analysis(result_db, "worker-retry") == analysis.id
    analysis_orchestrator.process_analysis(analysis.id, "worker-retry")
    with isolated() as result_db:
        result = result_db.get(ImageAnalysis, analysis.id)
        assert result.overall_status == "failed" and result.attempt_count == 2
        with pytest.raises(ValueError, match="retry limit"):
            analysis_orchestrator.retry_analysis(result_db, result)


def test_storage_failure_does_not_create_image_record(database, monkeypatch):
    def fail(*_args):
        raise storage_service.StorageError("disk unavailable")
    monkeypatch.setattr(image_routes, "store_image", fail)
    with pytest.raises(HTTPException) as failure:
        image_routes.upload_image(UploadFile(filename="sample.jpg", file=io.BytesIO(jpeg_bytes())), database)
    assert failure.value.status_code == 503
    assert database.query(ImageAsset).count() == 0


def test_foreign_key_prevents_unknown_image_reference(database):
    job = ResearchJob(id="ae28eb9e-2a60-4f04-8de8-a57e04d717aa", title="Invalid image", image_id="missing-image", status="queued")
    database.add(job)
    with pytest.raises(IntegrityError):
        database.commit()
    database.rollback()


def test_openapi_contract_includes_lifecycle_and_metadata():
    schema = app.openapi()
    paths = schema["paths"]
    assert "/api/v1/images/{image_id}/metadata" in paths
    assert "/api/v1/research/{research_id}/status" in paths
    assert paths["/api/v1/research/{research_id}/status"]["patch"]["responses"]["410"]
    assert "/api/v1/research/{research_id}/analyze" in paths
    assert "/api/v1/research/{research_id}/analysis" in paths
    status_schema = schema["components"]["schemas"]["ResearchStatusUpdate"]["properties"]["status"]
    assert status_schema["enum"] == ["queued", "processing", "completed", "failed"]

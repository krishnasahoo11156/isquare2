import hashlib
import io
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
import app.api.routes.images as image_routes
import app.api.routes.analysis as analysis_routes
import app.services.storage_service as storage_service
from app.database.connection import Base
from app.database import connection

pytestmark = pytest.mark.skipif(
    os.getenv("ISQUARE_RUN_HTTP_TESTS") != "1",
    reason="Set ISQUARE_RUN_HTTP_TESTS=1 to run live FastAPI HTTP integration tests.",
)


def jpeg_bytes(size: tuple[int, int] = (32, 24)) -> bytes:
    image = Image.new("RGB", size, "white")
    output = io.BytesIO()
    image.save(output, format="JPEG")
    return output.getvalue()


def oversized_jpeg_dimensions() -> bytes:
    data = bytearray(jpeg_bytes())
    marker = data.find(b"\xff\xc0")
    assert marker >= 0
    data[marker + 5:marker + 7] = (6400).to_bytes(2, "big")
    data[marker + 7:marker + 9] = (6400).to_bytes(2, "big")
    return bytes(data)


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(main_module, "engine", engine)
    monkeypatch.setattr(connection, "SessionLocal", session_factory)
    upload_dir = tmp_path / "uploads"
    monkeypatch.setattr(storage_service, "STORAGE", upload_dir)
    monkeypatch.setattr(image_routes, "STORAGE", upload_dir)
    monkeypatch.setattr(analysis_routes, "STORAGE", upload_dir)
    with TestClient(main_module.app, raise_server_exceptions=False) as test_client:
        yield test_client
    engine.dispose()


def test_health_endpoint(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "application": "iSquare", "version": "0.1.0"}


def test_upload_metadata_hash_duplicate_and_inline_image(client: TestClient, tmp_path: Path):
    payload = jpeg_bytes()
    upload = client.post("/api/v1/images/upload", files={"file": ("sample.jpg", payload, "application/octet-stream")})
    assert upload.status_code == 201
    result = upload.json()
    assert result["sha256"] == hashlib.sha256(payload).hexdigest()
    assert (result["width"], result["height"]) == (32, 24)
    assert result["mime_type"] == "image/jpeg"

    metadata = client.get(f"/api/v1/images/{result['id']}/metadata")
    assert metadata.status_code == 200
    assert metadata.json()["sha256"] == result["sha256"]
    assert isinstance(metadata.json()["exif"], dict)

    image_response = client.get(f"/api/v1/images/{result['id']}/thumbnail")
    assert image_response.status_code == 200
    assert image_response.headers["content-type"] == "image/jpeg"
    assert image_response.headers["content-disposition"].startswith("inline")
    with Image.open(io.BytesIO(image_response.content)) as preview:
        assert preview.width <= 160 and preview.height <= 160

    duplicate = client.post("/api/v1/images/upload", files={"file": ("renamed.jpg", payload, "image/jpeg")})
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == result["id"]
    assert len(list((tmp_path / "uploads").glob("*"))) == 1


def test_upload_rejections(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    bad = client.post("/api/v1/images/upload", files={"file": ("bad.png", b"not an image", "image/png")})
    assert bad.status_code == 422
    assert bad.json()["detail"]["code"] == "invalid_image"

    monkeypatch.setattr(image_routes, "MAX_BYTES", 64)
    oversized = client.post("/api/v1/images/upload", files={"file": ("large.jpg", jpeg_bytes(), "image/jpeg")})
    assert oversized.status_code == 413


def test_dimension_rejection(client: TestClient):
    response = client.post("/api/v1/images/upload", files={"file": ("dimensions.jpg", oversized_jpeg_dimensions(), "image/jpeg")})
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "invalid_dimensions"


def test_storage_failure_is_structured(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    def fail_storage(*_args):
        raise storage_service.StorageError("private filesystem detail")
    monkeypatch.setattr(image_routes, "store_image", fail_storage)
    response = client.post("/api/v1/images/upload", files={"file": ("sample.jpg", jpeg_bytes(), "image/jpeg")})
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "storage_unavailable"
    assert "private filesystem detail" not in response.text


def test_research_persistence_pagination_and_not_found(client: TestClient):
    uploaded = client.post("/api/v1/images/upload", files={"file": ("sample.jpg", jpeg_bytes(), "image/jpeg")})
    image_id = uploaded.json()["id"]
    ids = []
    for index in range(3):
        created = client.post("/api/v1/research", json={"image_id": image_id, "subject_name": f"Subject {index}"})
        assert created.status_code == 201
        assert created.json()["status"] == "queued"
        created_at = datetime.fromisoformat(created.json()["created_at"].replace("Z", "+00:00"))
        assert created_at.tzinfo is not None and created_at.utcoffset() == timezone.utc.utcoffset(created_at)
        ids.append(created.json()["id"])

    page = client.get("/api/v1/research?limit=1&offset=1")
    assert page.status_code == 200
    assert page.json()["total"] == 3
    assert len(page.json()["items"]) == 1
    assert page.json()["offset"] == 1
    assert client.get(f"/api/v1/research/{ids[1]}").json()["id"] == ids[1]
    assert client.get("/api/v1/research/not-a-record").status_code == 404
    assert client.get("/api/v1/images/not-an-image/metadata").status_code == 404

    persisted = client.get(f"/api/v1/research/{ids[0]}")
    assert persisted.status_code == 200
    assert persisted.json()["image"]["id"] == image_id


def test_research_status_transitions_are_validated(client: TestClient):
    uploaded = client.post("/api/v1/images/upload", files={"file": ("sample.jpg", jpeg_bytes(), "image/jpeg")})
    created = client.post("/api/v1/research", json={"image_id": uploaded.json()["id"]})
    research_id = created.json()["id"]

    invalid_value = client.patch(f"/api/v1/research/{research_id}/status", json={"status": "unknown"})
    assert invalid_value.status_code == 422
    processing = client.patch(f"/api/v1/research/{research_id}/status", json={"status": "processing"})
    assert processing.status_code == 410
    completed = client.patch(f"/api/v1/research/{research_id}/status", json={"status": "completed"})
    assert completed.status_code == 410
    assert client.get(f"/api/v1/research/{research_id}").json()["status"] == "queued"


def test_analysis_api_queues_idempotently_and_persists_results(client: TestClient):
    uploaded = client.post("/api/v1/images/upload", files={"file": ("sample.jpg", jpeg_bytes(), "image/jpeg")})
    research_id = client.post("/api/v1/research", json={"image_id": uploaded.json()["id"]}).json()["id"]
    first = client.post(f"/api/v1/research/{research_id}/analyze")
    assert first.status_code == 202
    body = first.json()
    assert body["status"] == "queued"
    duplicate = client.post(f"/api/v1/research/{research_id}/analyze")
    assert duplicate.status_code == 202
    assert duplicate.json()["analysis_id"] == body["analysis_id"]
    status_response = client.get(f"/api/v1/research/{research_id}/analysis/status")
    assert status_response.status_code == 200 and status_response.json()["status"] == "queued"
    result = client.get(f"/api/v1/research/{research_id}/analysis")
    assert result.status_code == 200
    assert result.json()["task_statuses"]["ocr"] == "pending"
    assert result.json()["classification"] is None
    assert client.get(f"/api/v1/analysis/{body['analysis_id']}").json()["id"] == body["analysis_id"]
    summary = client.get("/api/v1/analysis/summary").json()
    assert summary["total_research"] == 1 and summary["queued_analyses"] == 1
    assert client.get(f"/api/v1/research/{research_id}/analysis/status").status_code == 200
    assert client.get("/api/v1/analysis/missing").status_code == 404


def test_sqlite_foreign_keys_enabled(client: TestClient):
    with main_module.engine.connect() as db:
        assert db.scalar(text("PRAGMA foreign_keys")) == 1

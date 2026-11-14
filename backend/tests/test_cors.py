import io
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
import app.api.routes.images as image_routes
import app.api.routes.analysis as analysis_routes
import app.services.storage_service as storage_service
from app.database.connection import init_db
from app.database import connection
from app.models.image import ImageAsset
from app.models.research import ResearchJob
from app.models.analysis import ImageAnalysis, OCRResult


@pytest.fixture
def test_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")
    init_db(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(main_module, "engine", engine)
    monkeypatch.setattr(connection, "SessionLocal", session_factory)
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(storage_service, "STORAGE", upload_dir)
    monkeypatch.setattr(image_routes, "STORAGE", upload_dir)
    monkeypatch.setattr(analysis_routes, "STORAGE", upload_dir)
    with TestClient(main_module.app, raise_server_exceptions=False) as client:
        yield client, session_factory, upload_dir
    engine.dispose()


def test_cors_allowed_origins(test_client):
    client, _, _ = test_client

    # 1. http://localhost:3000
    res_local = client.get("/api/v1/health", headers={"Origin": "http://localhost:3000"})
    assert res_local.status_code == 200
    assert res_local.headers.get("access-control-allow-origin") == "http://localhost:3000"

    # 2. http://127.0.0.1:3000
    res_ip = client.get("/api/v1/health", headers={"Origin": "http://127.0.0.1:3000"})
    assert res_ip.status_code == 200
    assert res_ip.headers.get("access-control-allow-origin") == "http://127.0.0.1:3000"


def test_cors_disallowed_origin(test_client):
    client, _, _ = test_client
    res = client.get("/api/v1/health", headers={"Origin": "http://unauthorized-domain.com"})
    assert res.status_code == 200
    assert "access-control-allow-origin" not in res.headers


def test_cors_options_preflight_analysis(test_client):
    client, _, _ = test_client

    # Preflight for GET /api/v1/research/{id}/analysis from http://localhost:3000
    res = client.options(
        "/api/v1/research/sample-job-id/analysis",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "GET" in res.headers.get("access-control-allow-methods", "")
    assert "content-type" in res.headers.get("access-control-allow-headers", "").lower()

    # Preflight for POST /api/v1/research/{id}/analyze from http://127.0.0.1:3000
    res_post = client.options(
        "/api/v1/research/sample-job-id/analyze",
        headers={
            "Origin": "http://127.0.0.1:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert res_post.status_code == 200
    assert res_post.headers.get("access-control-allow-origin") == "http://127.0.0.1:3000"
    assert "POST" in res_post.headers.get("access-control-allow-methods", "")

    # Preflight from disallowed origin should be rejected (400) without CORS headers
    res_disallowed = client.options(
        "/api/v1/research/sample-job-id/analysis",
        headers={
            "Origin": "http://attacker.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res_disallowed.status_code == 400
    assert "access-control-allow-origin" not in res_disallowed.headers


def test_cors_error_responses_include_headers(test_client):
    client, _, _ = test_client

    # 404 error on research analysis endpoint
    res_404 = client.get("/api/v1/research/nonexistent-id/analysis", headers={"Origin": "http://localhost:3000"})
    assert res_404.status_code == 404
    assert res_404.headers.get("access-control-allow-origin") == "http://localhost:3000"

    # 422 validation error
    res_422 = client.post("/api/v1/research", json={}, headers={"Origin": "http://localhost:3000"})
    assert res_422.status_code == 422
    assert res_422.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_internal_error_response_includes_headers(test_client, monkeypatch):
    client, _, _ = test_client

    # Force an unhandled 500 error in a route to ensure unexpected_error_handler attaches CORS
    def raise_unhandled(*args, **kwargs):
        raise RuntimeError("Simulated crash")

    monkeypatch.setattr(analysis_routes, "_get_research", raise_unhandled)
    res_500 = client.get("/api/v1/research/some-id/analysis", headers={"Origin": "http://localhost:3000"})
    assert res_500.status_code == 500
    assert res_500.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert res_500.json()["detail"]["code"] == "internal_error"


def test_cors_full_analysis_workflow_endpoints(test_client):
    client, session_factory, upload_dir = test_client

    # Create dummy image and research job in database
    img_path = upload_dir / "test.jpg"
    Image.new("RGB", (100, 100), "white").save(img_path)

    with session_factory() as db:
        asset = ImageAsset(
            id="asset-123",
            original_filename="test.jpg",
            stored_filename="test.jpg",
            mime_type="image/jpeg",
            file_size=1000,
            width=100,
            height=100,
            sha256="dummyhash",
            storage_path=str(img_path),
        )
        job = ResearchJob(
            id="job-123",
            title="Test Research",
            image_id="asset-123",
            status="queued",
        )
        db.add(asset)
        db.add(job)
        db.commit()

    # 1. GET analysis when not yet queued -> 404 with CORS
    r_not_queued = client.get("/api/v1/research/job-123/analysis", headers={"Origin": "http://localhost:3000"})
    assert r_not_queued.status_code == 404
    assert r_not_queued.headers.get("access-control-allow-origin") == "http://localhost:3000"

    # 2. POST analyze -> 202 Accepted with CORS
    r_queue = client.post("/api/v1/research/job-123/analyze", headers={"Origin": "http://localhost:3000"})
    assert r_queue.status_code == 202
    assert r_queue.headers.get("access-control-allow-origin") == "http://localhost:3000"
    analysis_id = r_queue.json()["analysis_id"]

    # 3. GET analysis status -> 200 OK with CORS
    r_status = client.get("/api/v1/research/job-123/analysis/status", headers={"Origin": "http://localhost:3000"})
    assert r_status.status_code == 200
    assert r_status.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert r_status.json()["status"] == "queued"

    # 4. GET analysis results -> 200 OK with CORS
    r_results = client.get("/api/v1/research/job-123/analysis", headers={"Origin": "http://localhost:3000"})
    assert r_results.status_code == 200
    assert r_results.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert r_results.json()["id"] == analysis_id


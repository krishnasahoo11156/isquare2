import hashlib, io
from fastapi import HTTPException
from starlette.datastructures import UploadFile
from PIL import Image
from app.api.routes.health import health
from app.api.routes.images import upload_image
from app.api.routes.research import create_research, list_research, get_research
from app.schemas.research import ResearchCreate

def jpeg_bytes():
    image = Image.new("RGB", (32, 24), "white")
    out = io.BytesIO(); image.save(out, format="JPEG"); return out.getvalue()

def test_health():
    assert health()["status"] == "ok"

def test_upload_and_research(tmp_path, monkeypatch):
    import app.services.storage_service as storage
    import app.services.image_service as image_service
    import app.api.routes.images as image_routes
    import app.database.connection as connection
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.database.connection import Base
    engine = create_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(connection, "SessionLocal", TestingSession)
    monkeypatch.setattr(storage, "STORAGE", tmp_path / "uploads")
    data = jpeg_bytes()
    with TestingSession() as db:
        image = upload_image(UploadFile(filename="sample.jpg",file=io.BytesIO(data)),db)
        assert image.sha256 == hashlib.sha256(data).hexdigest()
        assert (image.width, image.height) == (32,24)
        created = create_research(ResearchCreate(image_id=image.id,subject_name="Sample"),db)
        assert created.status == "queued"
        assert get_research(created.id,db).id == created.id
        assert list_research(20,0,db)["total"] == 1
        try:
            upload_image(UploadFile(filename="bad.png",file=io.BytesIO(b"not an image")),db)
            assert False, "malformed image should be rejected"
        except HTTPException as exc:
            assert exc.status_code == 422
        monkeypatch.setattr(image_routes, "MAX_BYTES", 10)
        try:
            upload_image(UploadFile(filename="large.jpg",file=io.BytesIO(data)),db)
            assert False, "oversized image should be rejected"
        except HTTPException as exc:
            assert exc.status_code == 413
        monkeypatch.setattr(image_routes, "MAX_BYTES", 10 * 1024 * 1024)
        monkeypatch.setattr(image_service, "MAX_PIXELS", 500)
        try:
            upload_image(UploadFile(filename="large-dimensions.jpg",file=io.BytesIO(data)),db)
            assert False, "oversized dimensions should be rejected"
        except HTTPException as exc:
            assert exc.status_code == 422

from fastapi import APIRouter
from app.core.config import settings
router = APIRouter()
@router.get("/api/v1/health")
def health():
    return {"status": "ok", "application": settings.app_name, "version": settings.app_version}

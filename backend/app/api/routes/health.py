from fastapi import APIRouter
import os
router = APIRouter()
@router.get("/api/v1/health")
def health():
    return {"status": "ok", "application": os.getenv("APP_NAME", "iSquare"), "version": os.getenv("APP_VERSION", "0.1.0")}

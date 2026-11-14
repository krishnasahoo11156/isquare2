import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.database.connection import Base, engine
from app.models import ImageAsset, ResearchJob, ImageAnalysis, ClassificationResult, DetectionResult, OCRResult, OCRTextBlock, VisualObservation, ModelExecution
from app.api.routes import health, images, research, analysis
from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_credentials=False, allow_methods=["GET","POST","PATCH","OPTIONS"], allow_headers=["*"])
app.include_router(health.router); app.include_router(images.router); app.include_router(research.router); app.include_router(analysis.router)

@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail":{"code":"validation_error","message":"Request fields are invalid."}})

@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception):
    logger.error("Unhandled request error", exc_info=(type(exc), exc, exc.__traceback__))
    return JSONResponse(status_code=500, content={"detail":{"code":"internal_error","message":"The request could not be completed."}})

@app.get("/")
def root():
    return {"application": settings.app_name, "version": settings.app_version, "description": "Visual Intelligence & Digital Research Engine"}

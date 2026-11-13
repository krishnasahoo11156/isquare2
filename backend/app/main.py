import logging, os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.database.connection import Base, engine
from app.models import ImageAsset, ResearchJob
from app.api.routes import health, images, research

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title=os.getenv("APP_NAME", "iSquare"), version=os.getenv("APP_VERSION", "0.1.0"), lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")], allow_credentials=False, allow_methods=["GET","POST","OPTIONS"], allow_headers=["*"])
app.include_router(health.router); app.include_router(images.router); app.include_router(research.router)

@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail":{"code":"validation_error","message":"Request fields are invalid."}})

@app.get("/")
def root():
    return {"application": os.getenv("APP_NAME", "iSquare"), "version": os.getenv("APP_VERSION", "0.1.0"), "description": "Visual Intelligence & Digital Research Engine"}

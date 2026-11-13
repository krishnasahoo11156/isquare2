from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from app.database.connection import get_db
from app.models.image import ImageAsset
from app.models.research import ResearchJob
from app.schemas.research import ResearchCreate, ResearchList, ResearchOut
from app.services.research_service import build_research_job

router = APIRouter()
@router.post("/api/v1/research", response_model=ResearchOut, status_code=201)
def create_research(payload: ResearchCreate, db: Session = Depends(get_db)):
    image = db.get(ImageAsset, payload.image_id)
    if image is None:
        raise HTTPException(404, detail={"code":"image_not_found","message":"Uploaded image was not found."})
    job = build_research_job(payload, image)
    db.add(job); db.commit(); db.refresh(job)
    return db.scalar(select(ResearchJob).options(joinedload(ResearchJob.image)).where(ResearchJob.id == job.id))

@router.get("/api/v1/research", response_model=ResearchList)
def list_research(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    total = db.scalar(select(func.count()).select_from(ResearchJob)) or 0
    items = db.scalars(select(ResearchJob).options(joinedload(ResearchJob.image)).order_by(ResearchJob.created_at.desc()).limit(limit).offset(offset)).unique().all()
    return {"items":items,"total":total,"limit":limit,"offset":offset}

@router.get("/api/v1/research/{research_id}", response_model=ResearchOut)
def get_research(research_id: str, db: Session = Depends(get_db)):
    item = db.scalar(select(ResearchJob).options(joinedload(ResearchJob.image)).where(ResearchJob.id == research_id))
    if item is None: raise HTTPException(404, detail={"code":"research_not_found","message":"Research record was not found."})
    return item

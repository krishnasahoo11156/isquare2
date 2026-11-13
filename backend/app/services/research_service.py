import uuid
from app.models.image import ImageAsset
from app.models.research import ResearchJob
from app.schemas.research import ResearchCreate

def build_research_job(payload: ResearchCreate, image: ImageAsset) -> ResearchJob:
    title = payload.subject_name or payload.event_name or image.original_filename
    return ResearchJob(id=str(uuid.uuid4()), title=title[:255], image_id=image.id, subject_name=payload.subject_name, event_name=payload.event_name, organization=payload.organization, public_profile_url=str(payload.public_profile_url) if payload.public_profile_url else None, additional_context=payload.additional_context, status="queued")

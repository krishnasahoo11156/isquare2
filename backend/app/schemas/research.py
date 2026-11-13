from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

class ImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    original_filename: str
    mime_type: str
    file_size: int
    width: int
    height: int
    sha256: str
    created_at: datetime

class ResearchCreate(BaseModel):
    image_id: str
    subject_name: str | None = Field(default=None, max_length=255)
    event_name: str | None = Field(default=None, max_length=255)
    organization: str | None = Field(default=None, max_length=255)
    public_profile_url: HttpUrl | None = None
    additional_context: str | None = Field(default=None, max_length=5000)

class ResearchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    image_id: str
    subject_name: str | None
    event_name: str | None
    organization: str | None
    public_profile_url: str | None
    additional_context: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    image: ImageOut

class ResearchList(BaseModel):
    items: list[ResearchOut]
    total: int
    limit: int
    offset: int

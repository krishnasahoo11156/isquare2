from datetime import datetime, timezone
from sqlalchemy import ForeignKey, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.connection import Base
from app.database.types import UTCDateTime

class ResearchJob(Base):
    __tablename__ = "research_jobs"
    __table_args__ = (Index("ix_research_created", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    image_id: Mapped[str] = mapped_column(ForeignKey("image_assets.id"), nullable=False, index=True)
    subject_name: Mapped[str | None] = mapped_column(String(255))
    event_name: Mapped[str | None] = mapped_column(String(255))
    organization: Mapped[str | None] = mapped_column(String(255))
    public_profile_url: Mapped[str | None] = mapped_column(String(2048))
    additional_context: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    image: Mapped["ImageAsset"] = relationship(back_populates="researches")

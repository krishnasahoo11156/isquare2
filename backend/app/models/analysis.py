from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base
from app.database.types import UTCDateTime


class ImageAnalysis(Base):
    __tablename__ = "image_analyses"
    __table_args__ = (
        UniqueConstraint("research_job_id", "analysis_version", name="uq_analysis_job_version"),
        Index("ix_analysis_queue", "overall_status", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    research_job_id: Mapped[str] = mapped_column(ForeignKey("research_jobs.id", ondelete="CASCADE"), nullable=False)
    image_asset_id: Mapped[str] = mapped_column(ForeignKey("image_assets.id", ondelete="RESTRICT"), nullable=False)
    analysis_version: Mapped[str] = mapped_column(String(32), default="v1", nullable=False)
    overall_status: Mapped[str] = mapped_column(String(16), default="queued", nullable=False, index=True)
    classification_status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    detection_status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    ocr_status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    observation_status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    lease_owner: Mapped[str | None] = mapped_column(String(128))
    lease_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    error_code: Mapped[str | None] = mapped_column(String(64))
    warning: Mapped[str | None] = mapped_column(Text)
    preprocessing: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    image_width: Mapped[int | None] = mapped_column(Integer)
    image_height: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    classification: Mapped["ClassificationResult | None"] = relationship(back_populates="analysis", cascade="all, delete-orphan", uselist=False)
    detections: Mapped[list["DetectionResult"]] = relationship(back_populates="analysis", cascade="all, delete-orphan")
    ocr: Mapped["OCRResult | None"] = relationship(back_populates="analysis", cascade="all, delete-orphan", uselist=False)
    observations: Mapped[list["VisualObservation"]] = relationship(back_populates="analysis", cascade="all, delete-orphan")
    executions: Mapped[list["ModelExecution"]] = relationship(back_populates="analysis", cascade="all, delete-orphan")


class ClassificationResult(Base):
    __tablename__ = "classification_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("image_analyses.id", ondelete="CASCADE"), unique=True, nullable=False)
    predicted_category: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    alternative_predictions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    processing_duration_ms: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    analysis: Mapped[ImageAnalysis] = relationship(back_populates="classification")


class DetectionResult(Base):
    __tablename__ = "detection_results"
    __table_args__ = (Index("ix_detection_analysis", "analysis_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("image_analyses.id", ondelete="CASCADE"), nullable=False)
    object_label: Mapped[str] = mapped_column(String(128), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    bounding_box: Mapped[dict] = mapped_column(JSON, nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), nullable=False)
    analysis: Mapped[ImageAnalysis] = relationship(back_populates="detections")


class OCRResult(Base):
    __tablename__ = "ocr_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("image_analyses.id", ondelete="CASCADE"), unique=True, nullable=False)
    full_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    language: Mapped[str | None] = mapped_column(String(64))
    engine_name: Mapped[str] = mapped_column(String(128), nullable=False)
    engine_version: Mapped[str | None] = mapped_column(String(64))
    processing_duration_ms: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    blocks: Mapped[list["OCRTextBlock"]] = relationship(back_populates="ocr", cascade="all, delete-orphan", order_by="OCRTextBlock.sequence_number")
    analysis: Mapped[ImageAnalysis] = relationship(back_populates="ocr")


class OCRTextBlock(Base):
    __tablename__ = "ocr_text_blocks"
    __table_args__ = (Index("ix_ocr_block_order", "ocr_result_id", "sequence_number"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ocr_result_id: Mapped[int] = mapped_column(ForeignKey("ocr_results.id", ondelete="CASCADE"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    bounding_box: Mapped[dict] = mapped_column(JSON, nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    ocr: Mapped[OCRResult] = relationship(back_populates="blocks")


class VisualObservation(Base):
    __tablename__ = "visual_observations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("image_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    supporting_result_reference: Mapped[str] = mapped_column(String(128), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), nullable=False)
    analysis: Mapped[ImageAnalysis] = relationship(back_populates="observations")


class ModelExecution(Base):
    __tablename__ = "model_executions"
    __table_args__ = (Index("ix_model_execution_analysis", "analysis_id", "task_type"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("image_analyses.id", ondelete="CASCADE"), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(64))
    task_type: Mapped[str] = mapped_column(String(32), nullable=False)
    execution_status: Mapped[str] = mapped_column(String(16), nullable=False)
    processing_duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), nullable=False)
    analysis: Mapped[ImageAnalysis] = relationship(back_populates="executions")

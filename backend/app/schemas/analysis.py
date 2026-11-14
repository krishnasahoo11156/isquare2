from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


AnalysisStatus = Literal["queued", "processing", "completed", "failed"]
TaskStatus = Literal["pending", "processing", "completed", "failed", "skipped"]


class AnalyzeAccepted(BaseModel):
    analysis_id: str
    research_job_id: str
    status: AnalysisStatus
    already_exists: bool


class Box(BaseModel):
    x: int
    y: int
    width: int
    height: int


class ClassificationOut(BaseModel):
    category: str
    confidence: float | None
    alternatives: list[dict]
    model_name: str
    model_version: str
    duration_ms: int | None
    status: TaskStatus


class DetectionOut(BaseModel):
    id: int
    label: str
    confidence: float
    box: Box
    model_name: str
    model_version: str


class OCRBlockOut(BaseModel):
    text: str
    confidence: float | None
    box: Box
    sequence: int


class OCROut(BaseModel):
    text: str
    language: str | None
    engine_name: str
    engine_version: str | None
    duration_ms: int | None
    status: TaskStatus
    blocks: list[OCRBlockOut]


class ObservationOut(BaseModel):
    category: str
    description: str
    confidence: float | None
    evidence_reference: str
    model_name: str
    model_version: str


class ExecutionOut(BaseModel):
    task_type: str
    model_name: str
    model_version: str | None
    status: TaskStatus
    duration_ms: int | None
    error_code: str | None


class AnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    research_job_id: str
    image_asset_id: str
    status: AnalysisStatus
    analysis_version: str
    task_statuses: dict[str, TaskStatus]
    image_dimensions: dict[str, int] | None
    preprocessing: list[str]
    classification: ClassificationOut | None
    human_presence: dict
    detections: list[DetectionOut]
    ocr: OCROut | None
    observations: list[ObservationOut]
    executions: list[ExecutionOut]
    started_at: datetime | None
    completed_at: datetime | None
    error_code: str | None
    warning: str | None


class AnalysisStatusOut(BaseModel):
    analysis_id: str
    research_job_id: str
    status: AnalysisStatus
    task_statuses: dict[str, TaskStatus]
    attempt_count: int
    started_at: datetime | None
    completed_at: datetime | None
    error_code: str | None
    warning: str | None

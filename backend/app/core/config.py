import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    app_name: str
    app_version: str
    database_url: str
    storage_dir: Path
    max_upload_size_mb: int
    frontend_origin: str
    analysis_max_dimension: int
    ocr_language: str
    tesseract_cmd: str | None
    worker_poll_seconds: float
    worker_lease_seconds: int
    worker_max_attempts: int
    worker_concurrency: int
    model_cache_dir: Path
    ocr_timeout_seconds: int

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @classmethod
    def from_environment(cls) -> "Settings":
        try:
            max_upload_size_mb = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
        except ValueError as exc:
            raise ValueError("MAX_UPLOAD_SIZE_MB must be a positive integer") from exc
        if max_upload_size_mb < 1:
            raise ValueError("MAX_UPLOAD_SIZE_MB must be a positive integer")
        def positive_int(name: str, default: str) -> int:
            try:
                value = int(os.getenv(name, default))
            except ValueError as exc:
                raise ValueError(f"{name} must be a positive integer") from exc
            if value < 1:
                raise ValueError(f"{name} must be a positive integer")
            return value
        return cls(
            app_name=os.getenv("APP_NAME", "iSquare"),
            app_version=os.getenv("APP_VERSION", "0.1.0"),
            database_url=os.getenv("DATABASE_URL", "sqlite:///./isquare.db"),
            storage_dir=Path(os.getenv("STORAGE_DIR", "./storage/uploads")).resolve(),
            max_upload_size_mb=max_upload_size_mb,
            frontend_origin=os.getenv("FRONTEND_ORIGIN", "http://localhost:3000").rstrip("/"),
            analysis_max_dimension=positive_int("ANALYSIS_MAX_DIMENSION", "2400"),
            ocr_language=os.getenv("ISQUARE_OCR_LANGUAGE", "eng").strip() or "eng",
            tesseract_cmd=os.getenv("TESSERACT_CMD") or None,
            worker_poll_seconds=max(0.1, float(os.getenv("ANALYSIS_WORKER_POLL_SECONDS", "2"))),
            worker_lease_seconds=positive_int("ANALYSIS_WORKER_LEASE_SECONDS", "900"),
            worker_max_attempts=positive_int("ANALYSIS_WORKER_MAX_ATTEMPTS", "2"),
            worker_concurrency=1,
            model_cache_dir=Path(os.getenv("MODEL_CACHE_DIR", "./storage/models")).resolve(),
            ocr_timeout_seconds=positive_int("ISQUARE_OCR_TIMEOUT_SECONDS", "120"),
        )

settings = Settings.from_environment()

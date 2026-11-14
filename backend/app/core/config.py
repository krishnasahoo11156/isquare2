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
    cors_origins: tuple[str, ...]
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
        raw_cors = os.getenv("CORS_ORIGINS")
        if raw_cors:
            candidate_origins = [o.strip().rstrip("/") for o in raw_cors.split(",") if o.strip()]
        else:
            primary_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000").strip().rstrip("/")
            candidate_origins = [primary_origin, "http://localhost:3000", "http://127.0.0.1:3000"]
        seen_origins: set[str] = set()
        unique_origins: list[str] = []
        for origin in candidate_origins:
            if origin and origin not in seen_origins:
                seen_origins.add(origin)
                unique_origins.append(origin)
        cors_origins = tuple(unique_origins)
        frontend_origin = cors_origins[0] if cors_origins else "http://localhost:3000"

        return cls(
            app_name=os.getenv("APP_NAME", "iSquare"),
            app_version=os.getenv("APP_VERSION", "0.1.0"),
            database_url=os.getenv("DATABASE_URL", "sqlite:///./isquare.db"),
            storage_dir=Path(os.getenv("STORAGE_DIR", "./storage/uploads")).resolve(),
            max_upload_size_mb=max_upload_size_mb,
            frontend_origin=frontend_origin,
            cors_origins=cors_origins,
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

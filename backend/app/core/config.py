"""KeeAInu Application Configuration."""

from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable overrides."""
    
    PROJECT_NAME: str = "KeeAInu"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Storage Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    RAW_MEDIA_DIR: Path = DATA_DIR / "media" / "raw"
    DERIVED_MEDIA_DIR: Path = DATA_DIR / "media" / "derived"
    THUMBNAILS_DIR: Path = DERIVED_MEDIA_DIR / "thumbnails"
    SAMPLES_DIR: Path = DERIVED_MEDIA_DIR / "samples"
    CONTACT_SHEETS_DIR: Path = DERIVED_MEDIA_DIR / "contact_sheets"
    SOURCE_FOOTAGE_DIR: Path = DATA_DIR / "source_footage"
    ARTIFACTS_DIR: Path = DATA_DIR / "artifacts"
    DB_DIR: Path = DATA_DIR / "db"
    DB_PATH: Path = DB_DIR / "keeainu.sqlite"
    
    # Ingestion Limits
    MAX_UPLOAD_SIZE_BYTES: int = 500 * 1024 * 1024  # 500 MB
    ALLOWED_VIDEO_EXTENSIONS: List[str] = [".mp4", ".avi", ".mov", ".mkv", ".wmv"]
    ALLOWED_IMAGE_EXTENSIONS: List[str] = [".jpg", ".jpeg", ".png", ".bmp", ".webp"]
    
    # CORS Configuration (Strict development origins)
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]
    
    # Inference Settings
    DEFAULT_INFERENCE_ENGINE: str = "mock"
    CONFIDENCE_THRESHOLD: float = 0.50

    # Roboflow SAM 3 & Hosted Vision Inference
    ROBOFLOW_API_KEY: Optional[str] = None
    ROBOFLOW_API_URL: str = "https://infer.roboflow.com"
    ROBOFLOW_MODEL_ID: str = "videoscope-defect-segmentation/1"
    ROBOFLOW_SAM_PROMPTS: List[str] = [
        "crack",
        "pitting",
        "corrosion",
        "erosion",
        "deposit",
        "mechanical defect"
    ]
    ROBOFLOW_TIMEOUT_SECONDS: float = 30.0
    ROBOFLOW_MAX_RETRIES: int = 2
    ROBOFLOW_CACHE_ENABLED: bool = True
    ROBOFLOW_ALLOW_CLOUD_INFERENCE: bool = False  # Privacy Gate: require explicit authorization
    ROBOFLOW_MAX_IMAGE_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB
    ROBOFLOW_RATE_LIMIT_PER_MINUTE: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

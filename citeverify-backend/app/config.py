from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ENV_PATH = _BACKEND_DIR / ".env"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", str(_ENV_PATH)),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "CiteVerify"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-this-in-production"

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # CORS
    cors_origins: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8501",
        "http://localhost:8080",
    ]

    # Upload
    max_upload_size_mb: int = 50
    upload_dir: str = "uploads"
    reports_dir: str = "reports"

    # Database
    database_url: str = "sqlite:///./citeverify.db"

    # External APIs
    semantic_scholar_api_key: str = ""
    crossref_email: str = ""

    # Rate limiting
    external_api_timeout_seconds: int = 30
    max_retries: int = 3

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    def ensure_directories(self) -> None:
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)
        Path(self.reports_dir).mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    return Settings()

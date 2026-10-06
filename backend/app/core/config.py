from pathlib import Path
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    PROJECT_NAME: str = "InsightFlow API"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "InsightFlow API - Analytics and Data Platform Backend"

    DATABASE_URL: Optional[str] = None

    # JWT Authentication Settings
    JWT_SECRET_KEY: str = "insightflow_super_secret_jwt_key_default_change_me_in_production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # CORS Settings
    CORS_ORIGINS: str = (
        "http://localhost,http://localhost:80,http://localhost:5173,http://localhost:3000,"
        "http://127.0.0.1,http://127.0.0.1:80,http://127.0.0.1:5173,http://127.0.0.1:3000"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    # File Storage Settings
    MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    UPLOAD_DIR: Optional[str] = None

    # AI Insights Settings
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    AI_MODEL: str = "gemini-1.5-flash"

    @property
    def upload_path(self) -> Path:
        """Resolve the uploads directory path outside source-code directory."""
        if self.UPLOAD_DIR:
            p = Path(self.UPLOAD_DIR)
        else:
            base_dir = Path(__file__).resolve().parent.parent.parent  # backend directory
            if (base_dir.parent / "storage" / "uploads").exists() or base_dir.parent.name == "Insightflow":
                p = base_dir.parent / "storage" / "uploads"
            else:
                p = base_dir / "storage" / "uploads"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        cleaned = v.strip()
        # Neon and Heroku style connection strings may start with postgres://
        # SQLAlchemy 2.x requires postgresql:// or postgresql+<driver>://
        if cleaned.startswith("postgres://"):
            cleaned = cleaned.replace("postgres://", "postgresql+psycopg2://", 1)
        elif cleaned.startswith("postgresql://") and not cleaned.startswith("postgresql+"):
            cleaned = cleaned.replace("postgresql://", "postgresql+psycopg2://", 1)
        return cleaned


settings = Settings()

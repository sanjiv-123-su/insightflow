from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    PROJECT_NAME: str = "InsightFlow API"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "InsightFlow API - Analytics and Data Platform Backend"

    DATABASE_URL: Optional[str] = None

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

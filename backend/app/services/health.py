import logging
from typing import Any, Tuple

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class HealthService:
    @staticmethod
    def get_root_message() -> dict[str, str]:
        return {"message": "InsightFlow API is running"}

    @staticmethod
    def get_health_status() -> dict[str, str]:
        return {"status": "healthy"}

    @staticmethod
    def test_database_connection(db: Session) -> Tuple[dict[str, Any], bool]:
        """Execute a simple query to verify Neon PostgreSQL connectivity without exposing credentials.
        
        Returns:
            Tuple of (response_data, is_healthy)
        """
        try:
            row = db.execute(
                text("SELECT 1 AS alive, current_database() AS db_name, version() AS version")
            ).mappings().one()

            version_str = str(row["version"]).split("\n")[0]
            # Truncate version string neatly if verbose
            if len(version_str) > 60:
                version_str = version_str[:60] + "..."

            return {
                "status": "healthy",
                "database": "connected",
                "message": "Successfully connected to Neon PostgreSQL.",
                "current_database": str(row["db_name"]),
                "server_version": version_str,
            }, True

        except SQLAlchemyError as exc:
            # Mask any internal credentials from logs/response
            logger.error("Database connection error: %s", exc)
            return {
                "status": "unhealthy",
                "database": "disconnected",
                "message": "Failed to connect to Neon PostgreSQL database.",
                "detail": "Connection error encountered. Verify DATABASE_URL, network connectivity, and Neon compute status.",
            }, False

        except Exception as exc:
            logger.error("Unexpected error during database check: %s", exc)
            return {
                "status": "unhealthy",
                "database": "disconnected",
                "message": "Unexpected error while testing database connection.",
                "detail": "An unexpected error occurred during database health check.",
            }, False

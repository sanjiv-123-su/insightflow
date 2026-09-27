from collections.abc import Generator
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """SQLAlchemy 2.x declarative base class for all future ORM models."""
    pass


_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker[Session]] = None


def get_engine() -> Engine:
    """Initialize or return the cached SQLAlchemy engine configured for Neon PostgreSQL.

    Neon-specific optimizations:
    - pool_pre_ping=True: Tests connections before using them from the pool,
      handling Neon serverless scale-to-zero / auto-suspend reconnects transparently.
    - pool_recycle=300: Recycles connections every 5 minutes to prevent stale connections
      behind cloud proxies and PgBouncer.
    """
    global _engine, _session_factory
    if _engine is None:
        if not settings.DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL is not configured. Please define DATABASE_URL in your environment or .env file."
            )
        _engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            pool_recycle=300,
        )
        _session_factory = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Return the configured sessionmaker."""
    global _session_factory
    if _session_factory is None:
        get_engine()
    assert _session_factory is not None
    return _session_factory


class _SessionLocalProxy:
    """Callable proxy for SessionLocal to support lazy initialization."""

    def __call__(self, *args, **kwargs) -> Session:
        factory = get_session_factory()
        return factory(*args, **kwargs)


SessionLocal = _SessionLocalProxy()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a transactional database session per request."""
    if not settings.DATABASE_URL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is not configured. DATABASE_URL is missing.",
        )
    factory = get_session_factory()
    db = factory()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# Initialize eagerly if DATABASE_URL is already provided in the environment
if settings.DATABASE_URL:
    try:
        get_engine()
    except Exception:
        pass

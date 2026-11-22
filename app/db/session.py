"""Database session management.

The engine is created lazily so the application can start (and serve the health
endpoint) even when DATABASE_URL is not yet configured. Database-dependent
features will raise a clear error if the database is not configured.
"""

from __future__ import annotations

from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

_engine = None
_SessionLocal: Optional[sessionmaker] = None


def get_engine():
    global _engine, _SessionLocal
    if _engine is not None:
        return _engine
    if not settings.DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not configured. Set it in your environment or .env file."
        )
    _engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine


def SessionLocal() -> Session:  # type: ignore[override]
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

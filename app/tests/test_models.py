"""Model and database configuration tests."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, inspect

from app.db.base import Base
import app.models  # noqa: F401


def test_all_models_registered() -> None:
    expected = {
        "users",
        "provider_profiles",
        "services",
        "working_hours",
        "blocked_times",
        "appointments",
        "notifications",
    }
    assert expected.issubset(set(Base.metadata.tables.keys()))


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not configured; skipping database tests",
)
def test_database_tables_can_be_created() -> None:
    engine = create_engine(os.environ["DATABASE_URL"])
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert "users" in tables
    assert "appointments" in tables
    Base.metadata.drop_all(bind=engine)
    engine.dispose()

"""Appointment tests (SQLite-based; concurrency/locking needs PostgreSQL)."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.db.base import Base
import app.models
from app.db.session import get_engine, SessionLocal
from app.main import app
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.provider import ProviderProfile
from app.models.service import Service
from app.models.working_hours import WorkingHours


def _setup_provider():
    db = SessionLocal()
    u = User(name="Dr X", email="drx@example.com", password_hash=get_password_hash("secret123"), role=UserRole.PROVIDER)
    db.add(u); db.commit(); db.refresh(u)
    p = ProviderProfile(user_id=u.id, specialty="Cardio", timezone="UTC", is_approved=True)
    db.add(p); db.commit(); db.refresh(p)
    s = Service(provider_id=p.id, name="Consult", duration_minutes=30, price=100)
    db.add(s); db.commit(); db.refresh(s)
    # weekday Monday
    wh = WorkingHours(provider_id=p.id, weekday=0, start_time=__import__("datetime").time(9, 0), end_time=__import__("datetime").time(12, 0))
    db.add(wh); db.commit()
    db.close()
    return u, p, s


def _register_customer(client):
    client.post("/api/v1/auth/register", json={"name": "Alice", "email": "alice@example.com", "password": "secret123"})
    r = client.post("/api/v1/auth/login", json={"email": "alice@example.com", "password": "secret123"})
    return r.json()["access_token"]


@pytest.fixture(autouse=True)
def reset_db():
    os.environ.setdefault("ENVIRONMENT", "development")
    os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-1234567890")
    os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_booking_success_and_conflict():
    _setup_provider()
    client = TestClient(app)
    token = _register_customer(client)
    # find next Monday
    today = datetime.now(timezone.utc).date()
    mon = today + timedelta(days=7)
    start = datetime(mon.year, mon.month, mon.day, 10, 0, tzinfo=timezone.utc)
    # need provider/service ids
    db = SessionLocal()
    p = db.query(ProviderProfile).first()
    s = db.query(Service).first()
    pid, sid = str(p.id), str(s.id)
    db.close()

    r = client.post("/api/v1/appointments", headers={"Authorization": f"Bearer {token}"}, json={
        "provider_id": pid, "service_id": sid, "start_at": start.isoformat(), "customer_notes": "hi"
    })
    assert r.status_code == 201
    appt_id = r.json()["id"]

    # conflict same slot
    r2 = client.post("/api/v1/appointments", headers={"Authorization": f"Bearer {token}"}, json={
        "provider_id": pid, "service_id": sid, "start_at": start.isoformat()
    })
    assert r2.status_code == 409

    # cancel
    r3 = client.patch(f"/api/v1/appointments/{appt_id}/cancel", headers={"Authorization": f"Bearer {token}"}, json={"reason": "changed mind"})
    assert r3.status_code == 200
    assert r3.json()["status"] == "cancelled"

    # reschedule not allowed after cancel
    r4 = client.patch(f"/api/v1/appointments/{appt_id}/reschedule", headers={"Authorization": f"Bearer {token}"}, json={"start_at": (start + timedelta(hours=1)).isoformat()})
    assert r4.status_code == 400


def test_past_date_rejected():
    _setup_provider()
    client = TestClient(app)
    token = _register_customer(client)
    db = SessionLocal()
    p = db.query(ProviderProfile).first()
    s = db.query(Service).first()
    pid, sid = str(p.id), str(s.id)
    db.close()
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    r = client.post("/api/v1/appointments", headers={"Authorization": f"Bearer {token}"}, json={
        "provider_id": pid, "service_id": sid, "start_at": past
    })
    assert r.status_code == 400


def test_unauthorized_access():
    _setup_provider()
    client = TestClient(app)
    token = _register_customer(client)
    # /me requires auth
    r = client.get("/api/v1/appointments/me")
    assert r.status_code == 401
    r = client.get("/api/v1/appointments/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200

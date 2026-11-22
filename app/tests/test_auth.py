"""Authentication tests."""

from fastapi.testclient import TestClient

from app.db.base import Base
import app.models  # noqa: F401
from app.db.session import get_engine
from app.main import app


def _reset_db() -> None:
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_register_login_me() -> None:
    _reset_db()
    client = TestClient(app)
    r = client.post("/api/v1/auth/register", json={"name": "Alice", "email": "alice@example.com", "password": "secret123"})
    assert r.status_code == 201
    assert "password_hash" not in r.text

    r = client.post("/api/v1/auth/login", json={"email": "alice@example.com", "password": "secret123"})
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "alice@example.com"


def test_duplicate_email_returns_409() -> None:
    _reset_db()
    client = TestClient(app)
    client.post("/api/v1/auth/register", json={"name": "Bob", "email": "bob@example.com", "password": "secret123"})
    r = client.post("/api/v1/auth/register", json={"name": "Bob2", "email": "bob@example.com", "password": "secret123"})
    assert r.status_code == 409


def test_invalid_credentials_returns_401() -> None:
    _reset_db()
    client = TestClient(app)
    client.post("/api/v1/auth/register", json={"name": "Carol", "email": "carol@example.com", "password": "secret123"})
    r = client.post("/api/v1/auth/login", json={"email": "carol@example.com", "password": "wrong"})
    assert r.status_code == 401
    r = client.post("/api/v1/auth/login", json={"email": "nope@example.com", "password": "wrong"})
    assert r.status_code == 401

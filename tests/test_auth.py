import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base


@pytest.fixture
def client():
    from app.models import user, question, submission  # noqa
    # StaticPool forces all threads to share one connection — required so the
    # worker thread processing ASGI requests sees the same in-memory DB that the
    # fixture thread populated with create_all().
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    TestSession = sessionmaker(bind=test_engine)

    import app.database as db_module
    db_module.engine = test_engine
    db_module.SessionLocal = TestSession

    import app.seed as seed_module
    original_seed = seed_module.seed_admin
    seed_module.seed_admin = lambda db: None

    from app.main import app
    with TestClient(app) as c:
        yield c

    seed_module.seed_admin = original_seed
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def test_register_returns_201(client):
    """POST /auth/register creates a user and returns 201 with message."""
    resp = client.post("/auth/register", json={
        "name": "Alice", "email": "alice@test.com", "password": "pass123"
    })
    assert resp.status_code == 201
    assert resp.json()["message"] == "registered successfully"


def test_register_duplicate_returns_400(client):
    """POST /auth/register with duplicate email returns 400."""
    payload = {"name": "Alice", "email": "alice@test.com", "password": "pass123"}
    client.post("/auth/register", json=payload)
    resp = client.post("/auth/register", json=payload)
    assert resp.status_code == 400


def test_login_returns_jwt(client):
    """POST /auth/login returns access_token, token_type bearer, and role."""
    client.post("/auth/register", json={
        "name": "Bob", "email": "bob@test.com", "password": "pass123"
    })
    resp = client.post("/auth/login", json={"email": "bob@test.com", "password": "pass123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["role"] == "student"


def test_login_wrong_password_returns_401(client):
    """POST /auth/login with wrong password returns 401."""
    client.post("/auth/register", json={
        "name": "Bob", "email": "bob@test.com", "password": "pass123"
    })
    resp = client.post("/auth/login", json={"email": "bob@test.com", "password": "wrong"})
    assert resp.status_code == 401


def test_login_unknown_email_returns_401(client):
    """POST /auth/login with unknown email returns 401."""
    resp = client.post("/auth/login", json={"email": "nobody@test.com", "password": "pass"})
    assert resp.status_code == 401

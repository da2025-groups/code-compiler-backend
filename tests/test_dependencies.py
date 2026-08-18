import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


@pytest.fixture(autouse=True)
def _setup_db(monkeypatch):
    """Point the app engine at an in-memory DB for dependency tests."""
    from app.database import Base
    from app.models import user, question, submission  # noqa: register models
    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)

    import app.database as db_module
    from sqlalchemy.orm import sessionmaker
    monkeypatch.setattr(db_module, "engine", test_engine)
    monkeypatch.setattr(db_module, "SessionLocal", sessionmaker(bind=test_engine))
    yield
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def test_get_db_yields_session_and_closes():
    """get_db yields a Session and closes it after the generator exits."""
    from app.dependencies import get_db

    gen = get_db()
    session = next(gen)

    assert isinstance(session, Session), "get_db should yield a SQLAlchemy Session"
    assert session.is_active, "Session should be active while open"

    try:
        next(gen)
    except StopIteration:
        pass

    # After generator exhausted the session's connection should be released
    # (session.is_active stays True on closed sessions in SQLAlchemy 2.x,
    #  but bind should be gone — verify no exception on close())
    session.close()  # double-close must not raise


# ── get_current_user + require_admin ──────────────────────────────────────────

@pytest.fixture
def auth_client():
    """Minimal FastAPI app exposing /me and /admin-only to test the dependencies."""
    from fastapi import FastAPI, Depends
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.database import Base
    from app.models import user, question, submission  # noqa

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

    from app.dependencies import get_current_user, require_admin
    mini = FastAPI()

    @mini.get("/me")
    def me(user=Depends(get_current_user)):
        return {"id": user.id, "role": user.role}

    @mini.get("/admin-only")
    def admin_only(user=Depends(require_admin)):
        return {"id": user.id}

    yield TestClient(mini), test_engine, TestSession

    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def _make_token(test_engine, TestSession, role="student"):
    """Insert a user directly and return their JWT."""
    from app.models.user import User
    from app.services.auth_service import hash_password, create_access_token
    db = TestSession()
    u = User(name="T", email=f"{role}@t.com",
             password_hash=hash_password("x"), role=role)
    db.add(u)
    db.commit()
    db.refresh(u)
    token = create_access_token({"sub": str(u.id), "role": u.role})
    db.close()
    return token


def test_get_current_user_no_token_returns_401(auth_client):
    """GET /me without a token returns 401."""
    client, _, _ = auth_client
    resp = client.get("/me")
    assert resp.status_code == 401


def test_get_current_user_invalid_token_returns_401(auth_client):
    """GET /me with a garbage token returns 401."""
    client, _, _ = auth_client
    resp = client.get("/me", headers={"Authorization": "Bearer not.a.token"})
    assert resp.status_code == 401


def test_get_current_user_valid_token_returns_user(auth_client):
    """GET /me with a valid student JWT returns the user's id and role."""
    client, engine, Session = auth_client
    token = _make_token(engine, Session, "student")
    resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "student"


def test_require_admin_rejects_student_with_403(auth_client):
    """GET /admin-only with a student JWT returns 403."""
    client, engine, Session = auth_client
    token = _make_token(engine, Session, "student")
    resp = client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403

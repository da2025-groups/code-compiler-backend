import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    from app.models import user, question, submission  # noqa
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# ── password utils ────────────────────────────────────────────────────────────

def test_hash_and_verify_password():
    """hash_password produces verifiable hash; verify_password confirms match."""
    from app.services.auth_service import hash_password, verify_password
    hashed = hash_password("mysecret")
    assert hashed != "mysecret"
    assert verify_password("mysecret", hashed) is True
    assert verify_password("wrongpass", hashed) is False


# ── JWT utils ─────────────────────────────────────────────────────────────────

def test_create_and_decode_token(monkeypatch):
    """create_access_token produces a decodable JWT with correct claims."""
    import app.config as _config
    monkeypatch.setattr(_config, "settings", MagicMock(secret_key="test-secret"))
    from app.services.auth_service import create_access_token, decode_token
    token = create_access_token({"sub": "42", "role": "student"})
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "student"


def test_decode_invalid_token_raises(monkeypatch):
    """decode_token raises JWTError on a tampered/invalid token."""
    import app.config as _config
    from jose import JWTError
    monkeypatch.setattr(_config, "settings", MagicMock(secret_key="test-secret"))
    from app.services.auth_service import decode_token
    with pytest.raises(JWTError):
        decode_token("not.a.valid.token")


# ── register_user ─────────────────────────────────────────────────────────────

def test_register_creates_user(db):
    """register_user inserts a student user with hashed password."""
    from app.services.auth_service import register_user
    from app.schemas.auth import RegisterRequest
    from app.models.user import User
    register_user(db, RegisterRequest(name="Alice", email="alice@test.com", password="pass123"))
    user = db.query(User).filter(User.email == "alice@test.com").first()
    assert user is not None
    assert user.name == "Alice"
    assert user.role == "student"
    assert user.password_hash != "pass123"


def test_register_duplicate_email_raises_400(db):
    """register_user raises 400 if email already exists."""
    from app.services.auth_service import register_user
    from app.schemas.auth import RegisterRequest
    req = RegisterRequest(name="Alice", email="alice@test.com", password="pass123")
    register_user(db, req)
    with pytest.raises(HTTPException) as exc:
        register_user(db, req)
    assert exc.value.status_code == 400


# ── login_user ────────────────────────────────────────────────────────────────

def test_login_returns_token_response(db, monkeypatch):
    """login_user returns TokenResponse with valid JWT for correct credentials."""
    import app.config as _config
    monkeypatch.setattr(_config, "settings", MagicMock(
        secret_key="test-secret", admin_email="", admin_password="",
        piston_url="", database_url="",
    ))
    from app.services.auth_service import register_user, login_user, decode_token
    from app.schemas.auth import RegisterRequest, LoginRequest
    register_user(db, RegisterRequest(name="Bob", email="bob@test.com", password="pass123"))
    resp = login_user(db, LoginRequest(email="bob@test.com", password="pass123"))
    assert resp.token_type == "bearer"
    assert resp.role == "student"
    payload = decode_token(resp.access_token)
    assert payload["role"] == "student"


def test_login_wrong_password_raises_401(db, monkeypatch):
    """login_user raises 401 for wrong password."""
    import app.config as _config
    monkeypatch.setattr(_config, "settings", MagicMock(secret_key="test-secret"))
    from app.services.auth_service import register_user, login_user
    from app.schemas.auth import RegisterRequest, LoginRequest
    register_user(db, RegisterRequest(name="Bob", email="bob@test.com", password="pass123"))
    with pytest.raises(HTTPException) as exc:
        login_user(db, LoginRequest(email="bob@test.com", password="wrongpass"))
    assert exc.value.status_code == 401


def test_login_unknown_email_raises_401(db, monkeypatch):
    """login_user raises 401 for unknown email (no user exists)."""
    import app.config as _config
    monkeypatch.setattr(_config, "settings", MagicMock(secret_key="test-secret"))
    from app.services.auth_service import login_user
    from app.schemas.auth import LoginRequest
    with pytest.raises(HTTPException) as exc:
        login_user(db, LoginRequest(email="nobody@test.com", password="pass"))
    assert exc.value.status_code == 401

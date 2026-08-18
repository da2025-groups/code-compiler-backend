import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base


@pytest.fixture
def client():
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

    import app.seed as seed_module
    original_seed = seed_module.seed_admin
    seed_module.seed_admin = lambda db: None

    from app.main import app
    with TestClient(app) as c:
        yield c

    seed_module.seed_admin = original_seed
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


_ACCEPTED = {"stdout": "hello\n", "stderr": "", "execution_time_ms": 42, "status": "accepted"}
_RUNTIME_ERROR = {"stdout": "", "stderr": "NameError", "execution_time_ms": 10, "status": "runtime_error"}


async def test_playground_run_returns_execution_result(client):
    """POST /playground/run returns all four ExecutionResult fields."""
    with patch("app.services.piston_service.run_code", new=AsyncMock(return_value=_ACCEPTED)):
        resp = client.post("/playground/run", json={"language": "python", "code": "print('hello')"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["stdout"] == "hello\n"
    assert data["status"] == "accepted"
    assert isinstance(data["execution_time_ms"], int)
    assert "stderr" in data


async def test_playground_run_no_auth_required(client):
    """POST /playground/run succeeds without an Authorization header."""
    with patch("app.services.piston_service.run_code", new=AsyncMock(return_value=_ACCEPTED)):
        resp = client.post("/playground/run", json={"language": "python", "code": "pass"})
    assert resp.status_code == 200


async def test_playground_run_passes_stdin(client):
    """POST /playground/run forwards stdin to run_code."""
    mock = AsyncMock(return_value=_ACCEPTED)
    with patch("app.services.piston_service.run_code", new=mock):
        client.post("/playground/run", json={
            "language": "python", "code": "print(input())", "stdin": "42"
        })
    call_args = mock.call_args
    stdin_val = call_args.kwargs.get("stdin", call_args.args[2] if len(call_args.args) > 2 else "")
    assert stdin_val == "42"


async def test_playground_run_empty_stdin_default(client):
    """POST /playground/run with no stdin field defaults to empty string."""
    mock = AsyncMock(return_value=_ACCEPTED)
    with patch("app.services.piston_service.run_code", new=mock):
        client.post("/playground/run", json={"language": "python", "code": "pass"})
    call_args = mock.call_args
    stdin_val = call_args.kwargs.get("stdin", call_args.args[2] if len(call_args.args) > 2 else "")
    assert stdin_val == ""


async def test_playground_run_runtime_error_status(client):
    """POST /playground/run returns runtime_error status from piston."""
    with patch("app.services.piston_service.run_code", new=AsyncMock(return_value=_RUNTIME_ERROR)):
        resp = client.post("/playground/run", json={"language": "python", "code": "bad"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "runtime_error"

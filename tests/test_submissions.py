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


def _seed_question(client, sample_input="1\n", test_cases=None):
    import app.database as db_module
    from app.models.question import Question
    db = db_module.SessionLocal()
    q = Question(
        title="Sum Q",
        description="D",
        difficulty="easy",
        sample_input=sample_input,
        test_cases=test_cases or [{"input": "1\n", "output": "1"}],
        is_published=True,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    q_id = q.id
    db.close()
    return q_id


def _register_and_token(client, email="u@test.com", password="pass"):
    client.post("/auth/register", json={"name": "U", "email": email, "password": password})
    resp = client.post("/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


def _admin_token(client):
    import app.database as db_module
    from app.models.user import User
    from app.services.auth_service import hash_password, create_access_token
    db = db_module.SessionLocal()
    u = User(name="A", email="a@test.com", password_hash=hash_password("x"), role="admin")
    db.add(u); db.commit(); db.refresh(u)
    token = create_access_token({"sub": str(u.id), "role": u.role})
    db.close()
    return token


_EXEC = {"stdout": "1\n", "stderr": "", "execution_time_ms": 10, "status": "accepted"}


# ── POST /submissions/run ─────────────────────────────────────────────────────

def test_submission_run_returns_execution_result(client):
    """POST /submissions/run returns ExecutionResult-shaped dict."""
    q_id = _seed_question(client)
    token = _register_and_token(client)
    with patch("app.services.piston_service.run_code", new=AsyncMock(return_value=_EXEC)):
        resp = client.post("/submissions/run",
                           json={"question_id": q_id, "language": "python", "code": "pass"},
                           headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "stdout" in data and "status" in data and "execution_time_ms" in data


def test_submission_run_requires_auth(client):
    """POST /submissions/run without token returns 401."""
    q_id = _seed_question(client)
    resp = client.post("/submissions/run",
                       json={"question_id": q_id, "language": "python", "code": "pass"})
    assert resp.status_code == 401


def test_submission_run_404_for_unknown_question(client):
    """POST /submissions/run with unknown question_id returns 404."""
    token = _register_and_token(client)
    with patch("app.services.piston_service.run_code", new=AsyncMock(return_value=_EXEC)):
        resp = client.post("/submissions/run",
                           json={"question_id": 999, "language": "python", "code": "pass"},
                           headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


# ── POST /submissions/submit ──────────────────────────────────────────────────

def test_submission_submit_accepted_all_pass(client):
    """All test cases pass → status=accepted, score=100."""
    q_id = _seed_question(client, test_cases=[{"input": "1\n", "output": "1"}])
    token = _register_and_token(client)
    with patch("app.services.piston_service.run_code", new=AsyncMock(return_value=_EXEC)):
        resp = client.post("/submissions/submit",
                           json={"question_id": q_id, "language": "python", "code": "pass"},
                           headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "accepted"
    assert data["score"] == 100.0
    assert data["passed_cases"] == 1


def test_submission_submit_wrong_answer_partial(client):
    """1 of 2 test cases fail → status=wrong_answer, score=50."""
    q_id = _seed_question(client, test_cases=[
        {"input": "1\n", "output": "1"},
        {"input": "2\n", "output": "2"},
    ])
    token = _register_and_token(client)
    side_effects = [
        {"stdout": "1\n", "stderr": "", "execution_time_ms": 5, "status": "accepted"},
        {"stdout": "99\n", "stderr": "", "execution_time_ms": 5, "status": "accepted"},
    ]
    with patch("app.services.piston_service.run_code", new=AsyncMock(side_effect=side_effects)):
        resp = client.post("/submissions/submit",
                           json={"question_id": q_id, "language": "python", "code": "pass"},
                           headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "wrong_answer"
    assert data["score"] == 50.0


def test_submission_submit_requires_auth(client):
    """POST /submissions/submit without token returns 401."""
    q_id = _seed_question(client)
    resp = client.post("/submissions/submit",
                       json={"question_id": q_id, "language": "python", "code": "pass"})
    assert resp.status_code == 401


def test_submission_submit_persists_to_db(client):
    """After submit, GET /submissions/my returns the submission."""
    q_id = _seed_question(client)
    token = _register_and_token(client, email="v@test.com")
    with patch("app.services.piston_service.run_code", new=AsyncMock(return_value=_EXEC)):
        client.post("/submissions/submit",
                    json={"question_id": q_id, "language": "python", "code": "pass"},
                    headers={"Authorization": f"Bearer {token}"})
    resp = client.get("/submissions/my", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# ── GET /submissions/my ───────────────────────────────────────────────────────

def test_my_submissions_returns_list_with_question_title(client):
    """GET /submissions/my returns question_title in each item."""
    q_id = _seed_question(client)
    token = _register_and_token(client, email="w@test.com")
    with patch("app.services.piston_service.run_code", new=AsyncMock(return_value=_EXEC)):
        client.post("/submissions/submit",
                    json={"question_id": q_id, "language": "python", "code": "pass"},
                    headers={"Authorization": f"Bearer {token}"})
    resp = client.get("/submissions/my", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    item = resp.json()[0]
    assert item["question_title"] == "Sum Q"
    assert "submitted_at" in item


# ── GET /admin/submissions ────────────────────────────────────────────────────

def test_admin_submissions_returns_all(client):
    """GET /admin/submissions returns all submissions with user_name."""
    q_id = _seed_question(client)
    student_token = _register_and_token(client, email="x@test.com")
    with patch("app.services.piston_service.run_code", new=AsyncMock(return_value=_EXEC)):
        client.post("/submissions/submit",
                    json={"question_id": q_id, "language": "python", "code": "pass"},
                    headers={"Authorization": f"Bearer {student_token}"})
    admin_token = _admin_token(client)
    resp = client.get("/admin/submissions", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert "user_name" in resp.json()[0]


def test_admin_submissions_requires_admin(client):
    """GET /admin/submissions with student token returns 403."""
    token = _register_and_token(client, email="y@test.com")
    resp = client.get("/admin/submissions", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403

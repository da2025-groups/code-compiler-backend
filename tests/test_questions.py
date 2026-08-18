import pytest
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


def _seed_question(client, title="Q1", difficulty="easy", is_published=True,
                   test_cases=None):
    """Insert a question directly via the DB module (bypasses auth for seeding)."""
    import app.database as db_module
    from app.models.question import Question
    db = db_module.SessionLocal()
    q = Question(
        title=title,
        description="Description",
        difficulty=difficulty,
        is_published=is_published,
        test_cases=test_cases or [{"input": "1", "output": "1"}],
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    q_id = q.id
    db.close()
    return q_id


def _register_and_login(client, role="student"):
    email = f"{role}@test.com"
    client.post("/auth/register", json={"name": "T", "email": email, "password": "pass"})
    resp = client.post("/auth/login", json={"email": email, "password": "pass"})
    return resp.json()["access_token"]


# ── GET /questions ────────────────────────────────────────────────────────────

def test_list_questions_returns_published_only(client):
    """GET /questions returns only published questions."""
    _seed_question(client, title="Published", is_published=True)
    _seed_question(client, title="Hidden", is_published=False)
    resp = client.get("/questions")
    assert resp.status_code == 200
    titles = [q["title"] for q in resp.json()]
    assert "Published" in titles
    assert "Hidden" not in titles


def test_list_questions_no_auth_required(client):
    """GET /questions succeeds without authentication."""
    resp = client.get("/questions")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_questions_is_solved_true_with_accepted_submission(client):
    """GET /questions marks is_solved=true when user has an accepted submission."""
    q_id = _seed_question(client)
    token = _register_and_login(client)

    # seed an accepted submission
    import app.database as db_module
    from app.models.submission import Submission
    from app.models.user import User
    db = db_module.SessionLocal()
    user = db.query(User).filter(User.email == "student@test.com").first()
    db.add(Submission(
        user_id=user.id, question_id=q_id, language="python", code="pass",
        status="accepted", passed_cases=1, total_cases=1, score=100.0, execution_time_ms=10,
    ))
    db.commit()
    db.close()

    resp = client.get("/questions", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    item = next(q for q in resp.json() if q["id"] == q_id)
    assert item["is_solved"] is True


# ── GET /questions/:id ────────────────────────────────────────────────────────

def test_get_question_returns_detail_without_test_cases(client):
    """GET /questions/:id returns detail fields but never test_cases."""
    q_id = _seed_question(client, title="Detail Q")
    resp = client.get(f"/questions/{q_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Detail Q"
    assert "description" in data
    assert "test_cases" not in data


def test_get_question_returns_404_for_unknown(client):
    """GET /questions/999 returns 404."""
    resp = client.get("/questions/999")
    assert resp.status_code == 404


def test_get_question_returns_404_for_unpublished(client):
    """GET /questions/:id returns 404 for unpublished question."""
    q_id = _seed_question(client, is_published=False)
    resp = client.get(f"/questions/{q_id}")
    assert resp.status_code == 404

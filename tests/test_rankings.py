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


def _seed_user_and_submission(client, name="Alice", score=100, question_id=1, time_ms=100):
    import app.database as db_module
    from app.models.user import User
    from app.models.submission import Submission
    from app.services.auth_service import hash_password
    db = db_module.SessionLocal()
    u = User(name=name, email=f"{name.lower()}@t.com",
             password_hash=hash_password("x"), role="student")
    db.add(u)
    db.commit()
    db.refresh(u)
    s = Submission(
        user_id=u.id, question_id=question_id,
        language="python", code="pass",
        status="accepted" if score == 100 else "wrong_answer",
        passed_cases=int(score), total_cases=100,
        score=float(score), execution_time_ms=time_ms,
    )
    db.add(s)
    db.commit()
    user_id = u.id  # capture before closing session
    db.close()
    return user_id


# ── GET /rankings ─────────────────────────────────────────────────────────────

def test_global_rankings_public_no_auth_needed(client):
    """GET /rankings succeeds without authentication."""
    resp = client.get("/rankings")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_global_rankings_empty_array_when_no_data(client):
    """GET /rankings returns [] when there are no submissions."""
    resp = client.get("/rankings")
    assert resp.json() == []


def test_global_rankings_returns_correct_ranking(client):
    """GET /rankings orders by total_score desc and includes required fields."""
    _seed_user_and_submission(client, "Alice", score=100, question_id=1)
    _seed_user_and_submission(client, "Bob", score=50, question_id=1)
    resp = client.get("/rankings")
    assert resp.status_code == 200
    rows = resp.json()
    assert rows[0]["name"] == "Alice"
    assert rows[0]["rank"] == 1
    assert rows[0]["total_score"] == 100.0
    assert rows[0]["solved_count"] == 1
    assert rows[1]["rank"] == 2


# ── GET /rankings/:question_id ────────────────────────────────────────────────

def test_question_rankings_public_no_auth_needed(client):
    """GET /rankings/:id succeeds without authentication."""
    resp = client.get("/rankings/1")
    assert resp.status_code == 200


def test_question_rankings_returns_correct_ranking(client):
    """GET /rankings/:id orders by best_score desc, execution_time_ms asc."""
    _seed_user_and_submission(client, "Alice", score=100, question_id=1, time_ms=200)
    _seed_user_and_submission(client, "Bob", score=100, question_id=1, time_ms=100)
    resp = client.get("/rankings/1")
    assert resp.status_code == 200
    rows = resp.json()
    assert rows[0]["name"] == "Bob"   # faster
    assert rows[0]["execution_time_ms"] == 100
    assert rows[0]["best_score"] == 100.0

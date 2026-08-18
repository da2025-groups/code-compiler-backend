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


def _admin_token(client):
    """Register an admin user and return their JWT."""
    import app.database as db_module
    from app.models.user import User
    from app.services.auth_service import hash_password, create_access_token
    db = db_module.SessionLocal()
    u = User(name="Admin", email="admin@test.com",
             password_hash=hash_password("pass"), role="admin")
    db.add(u)
    db.commit()
    db.refresh(u)
    token = create_access_token({"sub": str(u.id), "role": u.role})
    db.close()
    return token


def _student_token(client):
    client.post("/auth/register", json={"name": "S", "email": "s@test.com", "password": "pass"})
    resp = client.post("/auth/login", json={"email": "s@test.com", "password": "pass"})
    return resp.json()["access_token"]


_Q_BODY = {
    "title": "Two Sum",
    "description": "Find two numbers that add up to target.",
    "difficulty": "easy",
    "constraints": "1 <= n <= 100",
    "sample_input": "2 7 11 15\n9",
    "sample_output": "0 1",
    "test_cases": [{"input": "2 7 11 15\n9", "output": "0 1"}],
    "is_published": False,
}


# ── POST /admin/questions ─────────────────────────────────────────────────────

def test_admin_create_question_returns_201(client):
    """Admin can create a question and gets 201."""
    token = _admin_token(client)
    resp = client.post("/admin/questions", json=_Q_BODY,
                       headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Two Sum"
    assert data["difficulty"] == "easy"


def test_admin_create_question_invalid_difficulty_returns_422(client):
    """POST /admin/questions with invalid difficulty returns 422."""
    token = _admin_token(client)
    body = {**_Q_BODY, "difficulty": "extreme"}
    resp = client.post("/admin/questions", json=body,
                       headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 422


# ── GET /admin/questions ──────────────────────────────────────────────────────

def test_admin_list_questions_includes_unpublished(client):
    """GET /admin/questions returns all questions including unpublished."""
    token = _admin_token(client)
    client.post("/admin/questions", json=_Q_BODY,
                headers={"Authorization": f"Bearer {token}"})
    client.post("/admin/questions", json={**_Q_BODY, "title": "Pub Q", "is_published": True},
                headers={"Authorization": f"Bearer {token}"})
    resp = client.get("/admin/questions", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    titles = [q["title"] for q in resp.json()]
    assert "Two Sum" in titles
    assert "Pub Q" in titles


# ── PUT /admin/questions/:id ──────────────────────────────────────────────────

def test_admin_update_question_changes_title(client):
    """Admin can update a question's title."""
    token = _admin_token(client)
    create_resp = client.post("/admin/questions", json=_Q_BODY,
                              headers={"Authorization": f"Bearer {token}"})
    q_id = create_resp.json()["id"]
    updated_body = {**_Q_BODY, "title": "Updated Title", "is_published": True}
    resp = client.put(f"/admin/questions/{q_id}", json=updated_body,
                      headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"
    assert resp.json()["is_published"] is True


def test_admin_update_question_returns_404_for_unknown(client):
    """PUT /admin/questions/999 returns 404."""
    token = _admin_token(client)
    resp = client.put("/admin/questions/999", json=_Q_BODY,
                      headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


# ── Auth enforcement ──────────────────────────────────────────────────────────

def test_admin_routes_reject_student_with_403(client):
    """Student JWT is rejected with 403 on admin routes."""
    token = _student_token(client)
    resp = client.get("/admin/questions", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_admin_routes_reject_unauthenticated_with_401(client):
    """No token is rejected with 401 on admin routes."""
    resp = client.get("/admin/questions")
    assert resp.status_code == 401


# ── DELETE /admin/questions/:id ───────────────────────────────────────────────

def test_admin_delete_question_returns_200(client):
    """Admin can delete a question and gets {"message": "deleted"}."""
    token = _admin_token(client)
    create_resp = client.post("/admin/questions", json=_Q_BODY,
                              headers={"Authorization": f"Bearer {token}"})
    assert create_resp.status_code == 201
    q_id = create_resp.json()["id"]

    resp = client.delete(f"/admin/questions/{q_id}",
                         headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == {"message": "deleted"}


def test_admin_delete_question_is_gone_after_delete(client):
    """Deleted question no longer appears in admin list."""
    token = _admin_token(client)
    create_resp = client.post("/admin/questions", json=_Q_BODY,
                              headers={"Authorization": f"Bearer {token}"})
    q_id = create_resp.json()["id"]
    client.delete(f"/admin/questions/{q_id}",
                  headers={"Authorization": f"Bearer {token}"})

    list_resp = client.get("/admin/questions",
                           headers={"Authorization": f"Bearer {token}"})
    ids = [q["id"] for q in list_resp.json()]
    assert q_id not in ids


def test_admin_delete_question_returns_404_for_unknown(client):
    """DELETE /admin/questions/999 returns 404 when question does not exist."""
    token = _admin_token(client)
    resp = client.delete("/admin/questions/999",
                         headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Question not found"


def test_admin_delete_question_rejects_student_with_403(client):
    """Student JWT is rejected with 403 on DELETE admin route."""
    token = _student_token(client)
    resp = client.delete("/admin/questions/1",
                         headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403

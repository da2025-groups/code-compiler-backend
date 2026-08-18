import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base


@pytest.fixture
def db():
    from app.models import user, question, submission  # noqa
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _make_question(db, title="Q1", difficulty="easy", is_published=True, test_cases=None):
    from app.models.question import Question
    q = Question(
        title=title,
        description="Desc",
        difficulty=difficulty,
        is_published=is_published,
        test_cases=test_cases or [{"input": "1", "output": "1"}],
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


def _make_user(db):
    from app.models.user import User
    from app.services.auth_service import hash_password
    u = User(name="T", email="t@t.com", password_hash=hash_password("x"), role="student")
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _make_submission(db, user_id, question_id, status="accepted"):
    from app.models.submission import Submission
    s = Submission(
        user_id=user_id,
        question_id=question_id,
        language="python",
        code="pass",
        status=status,
        passed_cases=1,
        total_cases=1,
        score=100.0,
        execution_time_ms=10,
    )
    db.add(s)
    db.commit()
    return s


# ── list_published_questions ──────────────────────────────────────────────────

def test_list_published_questions_excludes_unpublished(db):
    _make_question(db, title="Published", is_published=True)
    _make_question(db, title="Hidden", is_published=False)
    from app.services.question_service import list_published_questions
    result = list_published_questions(db)
    titles = [q["title"] for q in result]
    assert "Published" in titles
    assert "Hidden" not in titles


def test_list_published_questions_is_solved_true_for_accepted(db):
    q = _make_question(db)
    u = _make_user(db)
    _make_submission(db, u.id, q.id, status="accepted")
    from app.services.question_service import list_published_questions
    result = list_published_questions(db, user_id=u.id)
    assert result[0]["is_solved"] is True


def test_list_published_questions_is_solved_false_when_no_submission(db):
    _make_question(db)
    u = _make_user(db)
    from app.services.question_service import list_published_questions
    result = list_published_questions(db, user_id=u.id)
    assert result[0]["is_solved"] is False


# ── get_published_question ────────────────────────────────────────────────────

def test_get_published_question_returns_none_for_unpublished(db):
    q = _make_question(db, is_published=False)
    from app.services.question_service import get_published_question
    assert get_published_question(db, q.id) is None


def test_get_published_question_excludes_test_cases(db):
    q = _make_question(db, is_published=True)
    from app.services.question_service import get_published_question
    result = get_published_question(db, q.id)
    assert result is not None
    assert "test_cases" not in result


# ── create_question ───────────────────────────────────────────────────────────

def test_create_question_persists_all_fields(db):
    u = _make_user(db)
    from app.services.question_service import create_question
    from app.schemas.question import QuestionCreate
    req = QuestionCreate(
        title="New Q", description="D", difficulty="medium",
        test_cases=[{"input": "1", "output": "1"}], is_published=True,
    )
    result = create_question(db, req, created_by=u.id)
    assert result["title"] == "New Q"
    assert result["is_published"] is True


def test_create_question_invalid_difficulty_raises_422(db):
    from fastapi import HTTPException
    from app.services.question_service import create_question
    from app.schemas.question import QuestionCreate
    req = QuestionCreate(title="X", description="D", difficulty="extreme")
    with pytest.raises(HTTPException) as exc:
        create_question(db, req, created_by=1)
    assert exc.value.status_code == 422


# ── update_question ───────────────────────────────────────────────────────────

def test_update_question_changes_fields(db):
    q = _make_question(db, title="Old")
    from app.services.question_service import update_question
    from app.schemas.question import QuestionUpdate
    req = QuestionUpdate(title="New", description="D", difficulty="hard", is_published=True)
    result = update_question(db, q.id, req)
    assert result["title"] == "New"
    assert result["difficulty"] == "hard"


# ── list_all_questions ────────────────────────────────────────────────────────

def test_list_all_questions_includes_unpublished(db):
    _make_question(db, title="Pub", is_published=True)
    _make_question(db, title="Unp", is_published=False)
    from app.services.question_service import list_all_questions
    titles = [q["title"] for q in list_all_questions(db)]
    assert "Pub" in titles
    assert "Unp" in titles

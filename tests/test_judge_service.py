import pytest
from unittest.mock import AsyncMock, patch
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


def _make_question(db, sample_input="1\n", test_cases=None, is_published=True):
    from app.models.question import Question
    q = Question(
        title="Test Q",
        description="D",
        difficulty="easy",
        sample_input=sample_input,
        test_cases=test_cases or [{"input": "1\n", "output": "1"}],
        is_published=is_published,
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


_ACCEPTED_RESULT = {"stdout": "1\n", "stderr": "", "execution_time_ms": 10, "status": "accepted"}
_WRONG_RESULT   = {"stdout": "99\n", "stderr": "", "execution_time_ms": 10, "status": "accepted"}


# ── run_against_sample ────────────────────────────────────────────────────────

async def test_run_against_sample_uses_sample_input(db):
    """run_against_sample passes question.sample_input as stdin to run_code."""
    q = _make_question(db, sample_input="42\n")
    mock = AsyncMock(return_value=_ACCEPTED_RESULT)
    with patch("app.services.piston_service.run_code", mock):
        from app.services.judge_service import run_against_sample
        await run_against_sample(q.id, "python", "pass", db)
    _, kwargs = mock.call_args
    assert kwargs.get("stdin") == "42\n"


async def test_run_against_sample_raises_404_for_unknown_question(db):
    from fastapi import HTTPException
    from app.services.judge_service import run_against_sample
    with pytest.raises(HTTPException) as exc:
        await run_against_sample(999, "python", "pass", db)
    assert exc.value.status_code == 404


# ── judge_submission ──────────────────────────────────────────────────────────

async def test_judge_submission_all_pass_returns_accepted(db):
    """All test cases pass → status=accepted, score=100."""
    q = _make_question(db, test_cases=[
        {"input": "1\n", "output": "1"},
        {"input": "2\n", "output": "2"},
    ])
    u = _make_user(db)
    mock = AsyncMock(side_effect=[
        {"stdout": "1\n", "stderr": "", "execution_time_ms": 5, "status": "accepted"},
        {"stdout": "2\n", "stderr": "", "execution_time_ms": 8, "status": "accepted"},
    ])
    with patch("app.services.piston_service.run_code", mock):
        from app.services.judge_service import judge_submission
        result = await judge_submission(q.id, "python", "pass", u.id, db)
    assert result["status"] == "accepted"
    assert result["score"] == 100.0
    assert result["passed_cases"] == 2


async def test_judge_submission_partial_pass_calculates_score(db):
    """1 of 2 cases pass → score=50, status=wrong_answer."""
    q = _make_question(db, test_cases=[
        {"input": "1\n", "output": "1"},
        {"input": "2\n", "output": "2"},
    ])
    u = _make_user(db)
    mock = AsyncMock(side_effect=[
        {"stdout": "1\n", "stderr": "", "execution_time_ms": 5, "status": "accepted"},
        {"stdout": "99\n", "stderr": "", "execution_time_ms": 5, "status": "accepted"},
    ])
    with patch("app.services.piston_service.run_code", mock):
        from app.services.judge_service import judge_submission
        result = await judge_submission(q.id, "python", "pass", u.id, db)
    assert result["status"] == "wrong_answer"
    assert result["score"] == 50.0
    assert result["passed_cases"] == 1


async def test_judge_submission_persists_to_db(db):
    """judge_submission writes a Submission row to the database."""
    from app.models.submission import Submission
    q = _make_question(db)
    u = _make_user(db)
    with patch("app.services.piston_service.run_code", AsyncMock(return_value=_ACCEPTED_RESULT)):
        from app.services.judge_service import judge_submission
        await judge_submission(q.id, "python", "pass", u.id, db)
    assert db.query(Submission).filter(Submission.user_id == u.id).count() == 1


async def test_judge_submission_trims_whitespace(db):
    """Trailing newline in stdout still matches expected without newline."""
    q = _make_question(db, test_cases=[{"input": "1\n", "output": "1"}])
    u = _make_user(db)
    # stdout has trailing newline, expected does not
    mock = AsyncMock(return_value={"stdout": "1\n", "stderr": "", "execution_time_ms": 5, "status": "accepted"})
    with patch("app.services.piston_service.run_code", mock):
        from app.services.judge_service import judge_submission
        result = await judge_submission(q.id, "python", "pass", u.id, db)
    assert result["results"][0]["verdict"] == "pass"

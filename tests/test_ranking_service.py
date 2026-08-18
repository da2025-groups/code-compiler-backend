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


def _make_user(db, name="Alice", email=None):
    from app.models.user import User
    from app.services.auth_service import hash_password
    u = User(name=name, email=email or f"{name.lower()}@t.com",
             password_hash=hash_password("x"), role="student")
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _make_submission(db, user_id, question_id, score, execution_time_ms=100):
    from app.models.submission import Submission
    s = Submission(
        user_id=user_id, question_id=question_id,
        language="python", code="pass",
        status="accepted" if score == 100 else "wrong_answer",
        passed_cases=int(score), total_cases=100,
        score=float(score), execution_time_ms=execution_time_ms,
    )
    db.add(s)
    db.commit()
    return s


# ── get_global_rankings ───────────────────────────────────────────────────────

def test_global_rankings_empty_when_no_submissions(db):
    from app.services.ranking_service import get_global_rankings
    assert get_global_rankings(db) == []


def test_global_rankings_correct_order_by_total_score(db):
    """User with higher total_score ranks first."""
    a = _make_user(db, "Alice")
    b = _make_user(db, "Bob")
    _make_submission(db, a.id, 1, score=100)
    _make_submission(db, b.id, 1, score=50)
    from app.services.ranking_service import get_global_rankings
    rows = get_global_rankings(db)
    assert rows[0]["user_id"] == a.id
    assert rows[0]["rank"] == 1
    assert rows[1]["rank"] == 2


def test_global_rankings_solved_count_only_counts_perfect(db):
    """solved_count increments only when best score == 100."""
    u = _make_user(db)
    _make_submission(db, u.id, 1, score=50)
    _make_submission(db, u.id, 2, score=100)
    from app.services.ranking_service import get_global_rankings
    rows = get_global_rankings(db)
    assert rows[0]["solved_count"] == 1  # only Q2


def test_global_rankings_takes_best_score_per_question(db):
    """Two submissions on same question — best score is used, not sum."""
    u = _make_user(db)
    _make_submission(db, u.id, 1, score=50)
    _make_submission(db, u.id, 1, score=100)
    from app.services.ranking_service import get_global_rankings
    rows = get_global_rankings(db)
    assert rows[0]["total_score"] == 100.0  # not 150


# ── get_question_rankings ─────────────────────────────────────────────────────

def test_question_rankings_empty_when_no_submissions(db):
    from app.services.ranking_service import get_question_rankings
    assert get_question_rankings(db, 999) == []


def test_question_rankings_correct_order(db):
    """Same score → faster execution_time_ms ranks higher."""
    a = _make_user(db, "Alice")
    b = _make_user(db, "Bob")
    _make_submission(db, a.id, 1, score=100, execution_time_ms=200)
    _make_submission(db, b.id, 1, score=100, execution_time_ms=100)
    from app.services.ranking_service import get_question_rankings
    rows = get_question_rankings(db, 1)
    assert rows[0]["user_id"] == b.id  # Bob is faster
    assert rows[0]["execution_time_ms"] == 100


def test_question_rankings_rank_is_1_indexed(db):
    """Rank starts at 1."""
    u = _make_user(db)
    _make_submission(db, u.id, 1, score=100)
    from app.services.ranking_service import get_question_rankings
    rows = get_question_rankings(db, 1)
    assert rows[0]["rank"] == 1

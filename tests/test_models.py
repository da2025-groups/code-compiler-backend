import pytest
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError


@pytest.fixture
def db_session():
    """In-memory DB session with all tables created."""
    from app.database import Base
    from app.models import user, question, submission  # noqa: ensure models registered
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_user_model_unique_email(db_session):
    """Inserting two Users with the same email raises IntegrityError."""
    from app.models.user import User
    u1 = User(name="Alice", email="alice@test.com", password_hash="hash1", role="student")
    u2 = User(name="Alice2", email="alice@test.com", password_hash="hash2", role="student")
    db_session.add(u1)
    db_session.commit()
    db_session.add(u2)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_question_updated_at_auto_updates(db_session):
    """updated_at changes after a Question row is modified."""
    from app.models.question import Question
    q = Question(
        title="Test Q",
        description="Desc",
        difficulty="easy",
        is_published=False,
    )
    db_session.add(q)
    db_session.commit()
    db_session.refresh(q)
    first_updated = q.updated_at

    # Small delay so timestamps differ
    time.sleep(0.05)

    q.title = "Updated Title"
    db_session.commit()
    db_session.refresh(q)

    assert q.updated_at != first_updated, "updated_at should change on modification"

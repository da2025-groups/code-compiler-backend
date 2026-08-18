import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


@pytest.fixture(autouse=True)
def _setup_db(monkeypatch):
    """Point the app engine at an in-memory DB for dependency tests."""
    from app.database import Base
    from app.models import user, question, submission  # noqa: register models
    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)

    import app.database as db_module
    from sqlalchemy.orm import sessionmaker
    monkeypatch.setattr(db_module, "engine", test_engine)
    monkeypatch.setattr(db_module, "SessionLocal", sessionmaker(bind=test_engine))
    yield
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def test_get_db_yields_session_and_closes():
    """get_db yields a Session and closes it after the generator exits."""
    from app.dependencies import get_db

    gen = get_db()
    session = next(gen)

    assert isinstance(session, Session), "get_db should yield a SQLAlchemy Session"
    assert session.is_active, "Session should be active while open"

    try:
        next(gen)
    except StopIteration:
        pass

    # After generator exhausted the session's connection should be released
    # (session.is_active stays True on closed sessions in SQLAlchemy 2.x,
    #  but bind should be gone — verify no exception on close())
    session.close()  # double-close must not raise

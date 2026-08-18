import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def in_memory_engine():
    """Fresh in-memory SQLite engine for each test."""
    from app.database import Base
    from app.models import user, question, submission  # noqa: register models with Base.metadata
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_db_creates_all_tables(in_memory_engine):
    """create_all produces users, questions, submissions tables."""
    table_names = inspect(in_memory_engine).get_table_names()
    assert "users" in table_names
    assert "questions" in table_names
    assert "submissions" in table_names

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def db():
    """Fresh in-memory session with all tables."""
    from app.database import Base
    from app.models import user, question, submission  # noqa
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_seed_creates_admin_on_first_run(db, monkeypatch):
    """seed_admin creates an admin user when none exists."""
    import app.config as cfg
    monkeypatch.setattr(cfg, "settings", cfg.Settings(
        secret_key="s",
        admin_email="admin@seed.test",
        admin_password="pass123",
    ))

    from app.seed import seed_admin
    seed_admin(db)

    from app.models.user import User
    admin = db.query(User).filter(User.email == "admin@seed.test").first()
    assert admin is not None, "Admin user should be created"
    assert admin.role == "admin"
    assert admin.password_hash != "pass123", "Password must be hashed"


def test_seed_is_idempotent(db, monkeypatch):
    """Calling seed_admin twice creates exactly one admin row."""
    import app.config as cfg
    monkeypatch.setattr(cfg, "settings", cfg.Settings(
        secret_key="s",
        admin_email="admin@seed.test",
        admin_password="pass123",
    ))

    from app.seed import seed_admin
    seed_admin(db)
    seed_admin(db)

    from app.models.user import User
    count = db.query(User).filter(User.email == "admin@seed.test").count()
    assert count == 1, f"Expected 1 admin row, got {count}"

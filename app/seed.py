import bcrypt
from sqlalchemy.orm import Session
import app.config as _config
from app.models.user import User


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def seed_admin(db: Session) -> None:
    """Create the admin account if it doesn't already exist."""
    s = _config.settings  # resolved at call time so tests can monkeypatch cfg.settings
    existing = db.query(User).filter(User.email == s.admin_email).first()
    if existing:
        return
    admin = User(
        name="Admin",
        email=s.admin_email,
        password_hash=_hash_password(s.admin_password),
        role="admin",
    )
    db.add(admin)
    db.commit()

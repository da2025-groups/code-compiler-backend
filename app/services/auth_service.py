import bcrypt
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from jose import jwt
from sqlalchemy.orm import Session

import app.config as _config
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse

_ALGORITHM = "HS256"
_ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, _config.settings.secret_key, algorithm=_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and verify a JWT. Raises jose.JWTError on invalid/expired token."""
    return jwt.decode(token, _config.settings.secret_key, algorithms=[_ALGORITHM])


def register_user(db: Session, req: RegisterRequest) -> None:
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        name=req.name,
        email=req.email,
        password_hash=hash_password(req.password),
        role="student",
    )
    db.add(user)
    db.commit()


def login_user(db: Session, req: LoginRequest) -> TokenResponse:
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return TokenResponse(access_token=token, token_type="bearer", role=user.role)

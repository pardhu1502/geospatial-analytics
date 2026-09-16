"""
Password hashing + JWT creation/decoding, and the `get_current_user` FastAPI
dependency used by every protected route.

Uses the same passlib `CryptContext` scheme (`bcrypt`) as
`app/scripts/seed_data.py` so hashes produced by either module are
interchangeable. See `requirements.txt` for the `bcrypt<4.1.0` pin note.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# tokenUrl points at the JSON login endpoint. It's only used by the OpenAPI
# docs UI to know where to POST credentials from the "Authorize" button; our
# actual /auth/login endpoint accepts a JSON body rather than an
# `application/x-www-form-urlencoded` OAuth2 form (see routers/auth.py).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

_SUB_CLAIM = "sub"


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str | int,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[dict[str, Any]] = None,
) -> str:
    """Create a signed JWT with `sub` set to the given subject (user id)."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode: dict[str, Any] = {_SUB_CLAIM: str(subject), "exp": expire}
    if extra_claims:
        to_encode.update(extra_claims)
    return jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT, raising `JWTError` on any failure."""
    return jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency: decode the bearer token and load the `User`.

    Raises 401 if the token is missing, invalid/expired, or no longer
    references an existing user.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_exception

    try:
        payload = decode_access_token(token)
        user_id_raw = payload.get(_SUB_CLAIM)
        if user_id_raw is None:
            raise credentials_exception
        user_id = int(user_id_raw)
    except (JWTError, ValueError, TypeError):
        raise credentials_exception

    user = db.get(User, user_id)
    if user is None:
        raise credentials_exception
    return user

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class UserLogin(BaseModel):
    """Body for POST /auth/login.

    ARCHITECTURE.md specifies `{email, password}` as a JSON body (not the
    OAuth2 `application/x-www-form-urlencoded` password-flow form), so this
    is what the router validates against. The FastAPI docs "Authorize"
    button still works against this endpoint via `OAuth2PasswordBearer`'s
    `tokenUrl` (see app/core/security.py) for interactive testing, but real
    clients should POST this JSON shape.
    """

    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    created_at: datetime

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    verify_token,
)
from app.models.user import AppUser
from app.schemas.auth import RefreshResponse, TokenResponse

settings = get_settings()

_failed_attempts: dict[str, list[datetime]] = {}
_lockout_until: dict[str, datetime] = {}

LOCKOUT_THRESHOLD = 5
LOCKOUT_DURATION_MINUTES = 15

# Dummy hash for timing-safe comparison when user doesn't exist
_DUMMY_HASH = bcrypt.hashpw(b"dummy", bcrypt.gensalt(rounds=12)).decode("utf-8")


def check_lockout(username: str) -> bool:
    lockout_time = _lockout_until.get(username)
    if lockout_time and datetime.now(timezone.utc) < lockout_time:
        return True
    elif lockout_time and datetime.now(timezone.utc) >= lockout_time:
        _lockout_until.pop(username, None)
        _failed_attempts.pop(username, None)
        return False
    return False


def record_failed_attempt(username: str) -> None:
    now = datetime.now(timezone.utc)
    if username not in _failed_attempts:
        _failed_attempts[username] = []
    cutoff = now - timedelta(minutes=LOCKOUT_DURATION_MINUTES)
    _failed_attempts[username] = [t for t in _failed_attempts[username] if t > cutoff]
    _failed_attempts[username].append(now)
    if len(_failed_attempts[username]) >= LOCKOUT_THRESHOLD:
        _lockout_until[username] = now + timedelta(minutes=LOCKOUT_DURATION_MINUTES)


def clear_failed_attempts(username: str) -> None:
    _failed_attempts.pop(username, None)
    _lockout_until.pop(username, None)


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[AppUser]:
    result = await db.execute(select(AppUser).where(AppUser.username == username))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        # Timing-safe: always run bcrypt comparison even for non-existent users
        verify_password(password, _DUMMY_HASH)
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_tokens(user: AppUser) -> TokenResponse:
    token_data = {
        "sub": user.username,
        "role": user.role,
        "party_code": user.party_code or "",
        "agent_code": user.agent_code or "",
    }
    access_token = create_access_token(token_data)
    refresh_token_str = create_refresh_token(token_data)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


async def refresh_access_token_db(token: str, db: AsyncSession) -> RefreshResponse:
    """Refresh token with database validation - ensures user still exists and is active."""
    from jose import JWTError
    try:
        payload = verify_token(token)
    except JWTError:
        raise ValueError("Invalid refresh token.")
    if payload.get("type") != "refresh":
        raise ValueError("Invalid refresh token type.")
    username = payload.get("sub")
    if not username:
        raise ValueError("Invalid refresh token claims.")
    
    # Verify user still exists and is active
    result = await db.execute(select(AppUser).where(AppUser.username == username))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise ValueError("User no longer active.")
    
    new_access_token = create_access_token({
        "sub": user.username,
        "role": user.role,
        "party_code": user.party_code or "",
        "agent_code": user.agent_code or "",
    })
    return RefreshResponse(
        access_token=new_access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

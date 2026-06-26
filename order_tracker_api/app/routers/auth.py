from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.auth import LoginRequest, MessageResponse, RefreshResponse, TokenResponse
from app.services.auth_service import (
    authenticate_user,
    check_lockout,
    clear_failed_attempts,
    create_tokens,
    record_failed_attempt,
    refresh_access_token_db,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    if check_lockout(request.username):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account temporarily locked. Try again in 15 minutes.",
        )
    user = await authenticate_user(db, request.username, request.password)
    if user is None:
        record_failed_attempt(request.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )
    clear_failed_attempts(request.username)
    return create_tokens(user)


@router.post("/refresh", response_model=RefreshResponse, status_code=status.HTTP_200_OK)
async def refresh(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await refresh_access_token_db(credentials.credentials, db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.post("/logout", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # Stateless logout - client clears tokens. Token blocklist can be added later with Redis.
    return MessageResponse(message="Logged out successfully")

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import AppUser
from app.models.sync_status import SyncStatus

router = APIRouter(prefix="/profile", tags=["Profile"])


class ProfileResponse(BaseModel):
    id: int
    username: str
    role: str
    full_name: str
    email: Optional[str] = None
    party_code: Optional[str] = None
    agent_code: Optional[str] = None


class SyncInfoResponse(BaseModel):
    last_sync_time: Optional[str] = None
    status: str = "never"


@router.get("/", response_model=ProfileResponse, status_code=status.HTTP_200_OK)
async def get_profile(current_user: AppUser = Depends(get_current_user)):
    return ProfileResponse(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        full_name=current_user.full_name,
        email=current_user.email,
        party_code=current_user.party_code,
        agent_code=current_user.agent_code,
    )


@router.get("/sync-info", response_model=SyncInfoResponse)
async def get_sync_info(
    current_user: AppUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SyncStatus).order_by(SyncStatus.id.desc()).limit(1))
    sync = result.scalar_one_or_none()
    if not sync or not sync.last_sync_time:
        return SyncInfoResponse(last_sync_time=None, status="never")
    return SyncInfoResponse(
        last_sync_time=sync.last_sync_time.isoformat() + "Z",
        status=sync.status,
    )

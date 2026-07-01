from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import AppUser
from app.schemas.outstanding import OutstandingListResponse
from app.services.outstanding_service import get_outstanding_bills

router = APIRouter(prefix="/outstanding", tags=["Outstanding"])


@router.get(
    "/",
    response_model=OutstandingListResponse,
    status_code=status.HTTP_200_OK,
    summary="List outstanding bills based on user role",
)
async def list_outstanding(
    current_user: AppUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_outstanding_bills(
        db=db,
        user=current_user,
    )

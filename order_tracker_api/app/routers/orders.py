from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import AppUser
from app.schemas.order import OrderListResponse, OrderResponse
from app.services.order_service import get_order_by_id, get_orders

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get("/", response_model=OrderListResponse, status_code=status.HTTP_200_OK)
async def list_orders(
    search: Optional[str] = None,
    sort_by: str = "order_date",
    sort_order: str = "desc",
    party_filter: Optional[str] = None,
    current_user: AppUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_orders(
        db=db,
        user=current_user,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        party_filter=party_filter,
    )


@router.get("/{order_id}", response_model=OrderResponse, status_code=status.HTTP_200_OK)
async def get_order(
    order_id: int,
    current_user: AppUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await get_order_by_id(db=db, order_id=order_id, user=current_user)
    return OrderResponse.model_validate(order)

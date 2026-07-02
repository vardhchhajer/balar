from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.user import AppUser
from app.schemas.order import OrderListResponse, OrderResponse

VALID_SORT_FIELDS = {"order_date", "dispatch_date"}
VALID_SORT_ORDERS = {"asc", "desc"}


async def get_orders(
    db: AsyncSession,
    user: AppUser,
    search: Optional[str] = None,
    sort_by: str = "order_date",
    sort_order: str = "desc",
    party_filter: Optional[str] = None,
) -> OrderListResponse:
    if sort_by not in VALID_SORT_FIELDS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid sort_by. Allowed: {', '.join(VALID_SORT_FIELDS)}.")
    if sort_order not in VALID_SORT_ORDERS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid sort_order. Allowed: {', '.join(VALID_SORT_ORDERS)}.")

    query = select(Order)

    # Role-based filtering
    if user.role == "party":
        query = query.where(Order.party_code == user.party_code)
    elif user.role == "agent":
        # Agent sees only orders for parties assigned to them
        query = query.where(Order.agent_code == user.agent_code)
        if party_filter:
            query = query.where(Order.party_code == party_filter)
    # Admin sees everything, no filter needed

    if search:
        query = query.where(Order.order_no.ilike(f"%{search}%"))

    sort_column = getattr(Order, sort_by)
    sort_func = asc if sort_order == "asc" else desc
    query = query.order_by(sort_func(sort_column), desc(Order.id))

    result = await db.execute(query)
    orders = result.scalars().all()
    order_responses = [OrderResponse.model_validate(order) for order in orders]
    return OrderListResponse(orders=order_responses, total=len(order_responses))


async def get_order_by_id(db: AsyncSession, order_id: int, user: AppUser) -> Order:
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    # Party can only see own orders
    if user.role == "party" and order.party_code != user.party_code:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    # Agent can only see orders for their parties
    if user.role == "agent" and order.agent_code != user.agent_code:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    return order

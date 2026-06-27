from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.core.security import get_password_hash
from app.models.user import AppUser
from app.models.sync_status import SyncStatus

router = APIRouter(prefix="/admin", tags=["Admin"])


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str  # agent or party
    party_code: Optional[str] = None
    agent_code: Optional[str] = None
    full_name: str
    email: Optional[str] = None


class UpdateUserRequest(BaseModel):
    is_active: Optional[bool] = None
    password: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    party_code: Optional[str]
    agent_code: Optional[str]
    full_name: str
    email: Optional[str]
    is_active: bool


class SyncStatusResponse(BaseModel):
    last_sync_time: Optional[str]
    status: str
    records_synced: int
    error_message: Optional[str]
    triggered_by: Optional[str]


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    admin: AppUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AppUser).order_by(AppUser.role, AppUser.username))
    users = result.scalars().all()
    return [UserResponse(
        id=u.id, username=u.username, role=u.role,
        party_code=u.party_code, agent_code=u.agent_code,
        full_name=u.full_name, email=u.email, is_active=u.is_active,
    ) for u in users]


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: CreateUserRequest,
    admin: AppUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if request.role not in ("agent", "party"):
        raise HTTPException(status_code=422, detail="Role must be 'agent' or 'party'.")
    existing = await db.execute(select(AppUser).where(AppUser.username == request.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already exists.")
    user = AppUser(
        username=request.username,
        password_hash=get_password_hash(request.password),
        role=request.role,
        party_code=request.party_code,
        agent_code=request.agent_code,
        full_name=request.full_name,
        email=request.email,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return UserResponse(
        id=user.id, username=user.username, role=user.role,
        party_code=user.party_code, agent_code=user.agent_code,
        full_name=user.full_name, email=user.email, is_active=user.is_active,
    )


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    request: UpdateUserRequest,
    admin: AppUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AppUser).where(AppUser.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if request.is_active is not None:
        user.is_active = request.is_active
    if request.password:
        user.password_hash = get_password_hash(request.password)
    if request.full_name:
        user.full_name = request.full_name
    if request.email is not None:
        user.email = request.email
    return UserResponse(
        id=user.id, username=user.username, role=user.role,
        party_code=user.party_code, agent_code=user.agent_code,
        full_name=user.full_name, email=user.email, is_active=user.is_active,
    )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    admin: AppUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AppUser).where(AppUser.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.role == "admin":
        raise HTTPException(status_code=403, detail="Cannot delete admin user.")
    await db.delete(user)
    return {"message": f"User {user.username} deleted."}


@router.get("/sync-status", response_model=SyncStatusResponse)
async def get_sync_status(
    admin: AppUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SyncStatus).order_by(SyncStatus.id.desc()).limit(1))
    sync = result.scalar_one_or_none()
    if not sync:
        return SyncStatusResponse(last_sync_time=None, status="never", records_synced=0, error_message=None, triggered_by=None)
    return SyncStatusResponse(
        last_sync_time=sync.last_sync_time.isoformat() if sync.last_sync_time else None,
        status=sync.status,
        records_synced=sync.records_synced,
        error_message=sync.error_message,
        triggered_by=sync.triggered_by,
    )


@router.post("/force-sync")
async def force_sync(
    admin: AppUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    sync = SyncStatus(
        status="requested",
        records_synced=0,
        triggered_by="admin_force",
    )
    db.add(sync)
    return {"message": "Sync requested. The sync agent will process this shortly."}


@router.post("/sync/receive")
async def receive_sync_data(
    data: dict,
    admin: AppUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Receive synced data from the on-premise sync agent."""
    from datetime import datetime
    from app.models.order import Order, OrderItem

    try:
        orders_data = data.get("orders", [])
        order_items_data = data.get("order_items", {})
        invoices_data = data.get("invoices", [])
        parties_data = data.get("parties", [])
        total_records = data.get("total_records", 0)

        # Clear existing synced orders and items
        existing_orders = await db.execute(select(Order))
        for order in existing_orders.scalars().all():
            await db.delete(order)

        # Insert fresh order data
        orders_created = 0
        items_created = 0

        for order_data in orders_data:
            erp_id = order_data.get("erp_order_id")
            order = Order(
                party_code=str(order_data.get("party_code", "")),
                order_no=order_data.get("order_no", f"ORD-{erp_id}"),
                order_date=datetime.fromisoformat(order_data["order_date"]).date() if order_data.get("order_date") else datetime.now().date(),
                dispatch_status="Stopped" if order_data.get("is_stopped") else (order_data.get("flag") or "Pending"),
                dispatch_date=datetime.fromisoformat(order_data["vch_date"]).date() if order_data.get("vch_date") else None,
                invoice_no=None,
                tracking_no=None,
                total_amount=float(order_data.get("total_qty", 0)) * float(order_items_data.get(str(erp_id), [{}])[0].get("rate", 0)) if order_items_data.get(str(erp_id)) else 0,
                remarks=order_data.get("narration"),
            )
            db.add(order)
            await db.flush()

            # Add items for this order
            items_for_order = order_items_data.get(str(erp_id), [])
            for item_data in items_for_order:
                item = OrderItem(
                    order_id=order.id,
                    product_name=item_data.get("product_name", "Unknown"),
                    quantity=item_data.get("bales", 0) or item_data.get("pieces", 0) or 1,
                    unit_price=float(item_data.get("rate", 0)),
                    amount=float(item_data.get("meter", 0)) * float(item_data.get("rate", 0)),
                )
                db.add(item)
                items_created += 1

            orders_created += 1

        # Update sync status
        sync = SyncStatus(
            last_sync_time=datetime.now(),
            status="success",
            records_synced=total_records,
            triggered_by="sync_agent",
        )
        db.add(sync)

        return {
            "message": "Sync received successfully",
            "orders_synced": orders_created,
            "items_synced": items_created,
            "invoices_received": len(invoices_data),
            "parties_received": len(parties_data),
        }

    except Exception as e:
        # Log the error in sync status
        sync = SyncStatus(
            last_sync_time=datetime.now(),
            status="failed",
            records_synced=0,
            error_message=str(e)[:500],
            triggered_by="sync_agent",
        )
        db.add(sync)
        raise HTTPException(status_code=500, detail=f"Sync processing failed: {str(e)[:100]}")

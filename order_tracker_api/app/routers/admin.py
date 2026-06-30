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


@router.post("/users/bulk")
async def bulk_create_users(
    data: dict,
    admin: AppUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Bulk create users - skips existing ones, fast bcrypt with lower rounds for bulk."""
    import bcrypt as _bcrypt
    
    users_list = data.get("users", [])
    created = 0
    skipped = 0
    
    # Get all existing usernames in one query
    result = await db.execute(select(AppUser.username))
    existing_usernames = {row[0] for row in result.fetchall()}
    
    for user_data in users_list:
        username = user_data.get("username", "")
        if not username or username in existing_usernames:
            skipped += 1
            continue
        
        password = user_data.get("password", "")
        # Use rounds=8 for bulk (fast, still adequate for internal app)
        salt = _bcrypt.gensalt(rounds=8)
        password_hash = _bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
        
        user = AppUser(
            username=username,
            password_hash=password_hash,
            role=user_data.get("role", "party"),
            party_code=user_data.get("party_code"),
            agent_code=user_data.get("agent_code"),
            full_name=user_data.get("full_name", ""),
            email=user_data.get("email"),
            is_active=True,
        )
        db.add(user)
        existing_usernames.add(username)
        created += 1
    
    return {"created": created, "skipped": skipped, "total": len(users_list)}


@router.post("/sync/receive")
async def receive_sync_data(
    data: dict,
    admin: AppUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Receive synced data from the on-premise sync agent. Uses upsert logic."""
    from datetime import datetime
    from sqlalchemy import delete
    from app.models.order import Order, OrderItem

    try:
        orders_data = data.get("orders", [])
        order_items_data = data.get("order_items", {})
        total_records = data.get("total_records", 0)

        orders_created = 0
        orders_updated = 0
        items_created = 0

        for order_data in orders_data:
            erp_id = order_data.get("erp_order_id")
            if not erp_id:
                continue

            # Get items by erp_order_id (direct FK from SALES_INVOICE_DETAIL.Sal_Order_Id)
            conf_no = order_data.get("conf_no")
            items_for_order = order_items_data.get(str(erp_id), []) if erp_id else []
            # Trust the sync's total strictly — it is the sum of real invoice
            # amounts (Sal_Inv_Amount), or 0 for orders not yet invoiced.
            # Do NOT recalculate; recalculating would invent a value for pending orders.
            total_amount = float(order_data.get("total_amount", 0))

            # Check if order already exists
            result = await db.execute(
                select(Order).where(Order.erp_order_id == erp_id)
            )
            existing_order = result.scalar_one_or_none()

            if existing_order:
                # Update existing order
                existing_order.party_code = str(order_data.get("party_code", ""))
                existing_order.party_name = order_data.get("party_name", "")
                existing_order.order_no = order_data.get("order_no", f"ORD-{erp_id}") or f"ORD-{erp_id}"
                existing_order.dispatch_status = "Stopped" if order_data.get("is_stopped") else (order_data.get("flag") or "Pending")
                existing_order.total_amount = total_amount
                existing_order.remarks = order_data.get("narration")
                if order_data.get("order_date"):
                    existing_order.order_date = datetime.fromisoformat(order_data["order_date"]).date()
                if order_data.get("dispatch_date"):
                    existing_order.dispatch_date = datetime.fromisoformat(order_data["dispatch_date"]).date()
                else:
                    existing_order.dispatch_date = None

                # Delete old items and re-insert
                await db.execute(delete(OrderItem).where(OrderItem.order_id == existing_order.id))
                order_id = existing_order.id
                orders_updated += 1
            else:
                # Insert new order
                new_order = Order(
                    erp_order_id=erp_id,
                    party_code=str(order_data.get("party_code", "")),
                    party_name=order_data.get("party_name", ""),
                    order_no=order_data.get("order_no", f"ORD-{erp_id}") or f"ORD-{erp_id}",
                    order_date=datetime.fromisoformat(order_data["order_date"]).date() if order_data.get("order_date") else datetime.now().date(),
                    dispatch_status="Stopped" if order_data.get("is_stopped") else (order_data.get("flag") or "Pending"),
                    dispatch_date=datetime.fromisoformat(order_data["dispatch_date"]).date() if order_data.get("dispatch_date") else None,
                    invoice_no=None,
                    tracking_no=None,
                    total_amount=total_amount,
                    remarks=order_data.get("narration"),
                )
                db.add(new_order)
                await db.flush()
                order_id = new_order.id
                orders_created += 1

            # Insert items — amounts come directly from ERP, no calculation
            for item_data in items_for_order:
                rate = float(item_data.get("rate", 0))
                qty = float(item_data.get("quantity", 0) or 1)
                amount = float(item_data.get("amount", 0))
                delivered = int(item_data.get("delivered_bales", 0) or 0)
                pending = int(item_data.get("pending_bales", 0) or 0)
                item = OrderItem(
                    order_id=order_id,
                    product_name=item_data.get("product_name", "Unknown"),
                    quantity=int(qty) if qty else 1,
                    unit_price=rate,
                    amount=amount,
                    delivered_qty=delivered,
                    pending_qty=pending,
                )
                db.add(item)
                items_created += 1

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
            "orders_created": orders_created,
            "orders_updated": orders_updated,
            "items_synced": items_created,
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Sync processing failed: {str(e)[:200]}")


@router.post("/sync/outstanding")
async def receive_outstanding_data(
    data: dict,
    admin: AppUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Receive outstanding bills from the on-premise sync agent. Replaces all bills per party."""
    from datetime import datetime
    from sqlalchemy import delete
    from app.models.outstanding import OutstandingBill

    try:
        bills_data = data.get("bills", [])

        # Group by party_code and delete existing, then re-insert
        party_codes_seen = set()
        bills_created = 0

        for bill_data in bills_data:
            party_code = str(bill_data.get("party_code", ""))
            if not party_code:
                continue

            # Delete existing bills for this party (first time we see them)
            if party_code not in party_codes_seen:
                await db.execute(
                    delete(OutstandingBill).where(OutstandingBill.party_code == party_code)
                )
                party_codes_seen.add(party_code)

            bill = OutstandingBill(
                party_code=party_code,
                bill_no=bill_data.get("bill_no", ""),
                bill_date=datetime.fromisoformat(bill_data["bill_date"]).date() if bill_data.get("bill_date") else datetime.now().date(),
                total_amount=float(bill_data.get("total_amount", 0)),
                amount_paid=float(bill_data.get("amount_paid", 0)),
                amount_outstanding=float(bill_data.get("amount_outstanding", 0)),
                due_date=datetime.fromisoformat(bill_data["due_date"]).date() if bill_data.get("due_date") else None,
                description=bill_data.get("description"),
            )
            db.add(bill)
            bills_created += 1

        return {
            "message": "Outstanding bills synced",
            "bills_created": bills_created,
            "parties_updated": len(party_codes_seen),
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Outstanding sync failed: {str(e)[:200]}")

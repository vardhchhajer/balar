from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outstanding import OutstandingBill
from app.models.user import AppUser
from app.schemas.outstanding import OutstandingBillResponse, OutstandingListResponse


async def get_outstanding_bills(
    db: AsyncSession,
    user: AppUser,
) -> OutstandingListResponse:
    """Get outstanding bills based on user role:
    - Party: sees only their own outstanding
    - Agent: sees only outstanding for parties assigned to them
    - Admin: sees everything
    """
    query = select(OutstandingBill)

    if user.role == "party":
        query = query.where(OutstandingBill.party_code == user.party_code)
    elif user.role == "agent":
        query = query.where(OutstandingBill.agent_code == user.agent_code)
    # Admin sees all

    query = query.order_by(OutstandingBill.due_date.asc())

    result = await db.execute(query)
    bills = result.scalars().all()

    bill_responses = [OutstandingBillResponse.model_validate(bill) for bill in bills]
    total_outstanding = sum(b.amount_outstanding for b in bill_responses)

    return OutstandingListResponse(
        bills=bill_responses,
        total_outstanding=total_outstanding,
        total=len(bill_responses),
    )

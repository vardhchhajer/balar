from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outstanding import OutstandingBill
from app.schemas.outstanding import OutstandingBillResponse, OutstandingListResponse


async def get_outstanding_bills(
    db: AsyncSession,
    party_code: str,
) -> OutstandingListResponse:
    """Get all outstanding bills for a party."""
    query = (
        select(OutstandingBill)
        .where(OutstandingBill.party_code == party_code)
        .order_by(OutstandingBill.due_date.asc())
    )

    result = await db.execute(query)
    bills = result.scalars().all()

    bill_responses = [OutstandingBillResponse.model_validate(bill) for bill in bills]
    total_outstanding = sum(b.amount_outstanding for b in bill_responses)

    return OutstandingListResponse(
        bills=bill_responses,
        total_outstanding=total_outstanding,
        total=len(bill_responses),
    )

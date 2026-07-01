from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_serializer


class OutstandingBillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    party_code: str
    bill_no: str
    bill_date: date
    total_amount: float
    amount_paid: float
    amount_outstanding: float
    due_date: Optional[date] = None
    description: Optional[str] = None

    @field_serializer("bill_date")
    def serialize_bill_date(self, v: date) -> str:
        return v.isoformat() if v else None

    @field_serializer("due_date")
    def serialize_due_date(self, v: Optional[date]) -> Optional[str]:
        return v.isoformat() if v else None


class OutstandingListResponse(BaseModel):
    bills: list[OutstandingBillResponse]
    total_outstanding: float
    total: int

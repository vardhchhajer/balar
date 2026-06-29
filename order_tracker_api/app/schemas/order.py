from pydantic import BaseModel, ConfigDict, field_serializer
from datetime import date
from typing import Optional


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_name: str
    quantity: int
    unit_price: float
    amount: float
    delivered_qty: int = 0
    pending_qty: int = 0


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_no: str
    order_date: date
    dispatch_status: str
    dispatch_date: Optional[date] = None
    invoice_no: Optional[str] = None
    tracking_no: Optional[str] = None
    total_amount: float = 0.0
    remarks: Optional[str] = None
    items: list[OrderItemResponse] = []

    @field_serializer("order_date")
    def serialize_order_date(self, v: date) -> str:
        return v.isoformat() if v else None

    @field_serializer("dispatch_date")
    def serialize_dispatch_date(self, v: Optional[date]) -> Optional[str]:
        return v.isoformat() if v else None


class OrderListResponse(BaseModel):
    orders: list[OrderResponse]
    total: int

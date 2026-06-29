from datetime import date, datetime
from typing import Optional

from sqlalchemy import String, Text, Date, Float, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    party_code: Mapped[str] = mapped_column(String(50), nullable=False)
    erp_order_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, unique=True)
    order_no: Mapped[str] = mapped_column(String(50), nullable=False)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    dispatch_status: Mapped[str] = mapped_column(String(50), nullable=False)
    dispatch_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    invoice_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tracking_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", lazy="selectin")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    delivered_qty: Mapped[int] = mapped_column(Integer, default=0)
    pending_qty: Mapped[int] = mapped_column(Integer, default=0)

    order: Mapped["Order"] = relationship(back_populates="items")
